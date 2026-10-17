from concurrent.futures import ThreadPoolExecutor
from typing import Any

from typesafe_sdk import TypeSafeError

from pipeline.config import BODY_CHARS, CONCURRENCY, QUESTIONS


def build_state(issue: dict) -> str:
    body = (issue.get("body") or "").strip()[:BODY_CHARS]
    return f"Title: {issue['title']}\n\n{body}" if body else f"Title: {issue['title']}"


def serialize_answers(response: Any) -> dict:
    out: dict = {}
    for name, ans in response.answers.items():
        if ans.type == "choice":
            out[name] = {
                "choice": ans.choice,
                "confidence": ans.confidence,
                "probabilities": ans.probabilities,
            }
        elif ans.type == "score":
            out[name] = {
                "score": ans.score,
                "confidence": ans.confidence,
                "probabilities": {str(k): v for k, v in ans.probabilities.items()},
            }
        elif ans.type == "noul":
            out[name] = {"noul": ans.noul}
    return out


def classify_issue(issue: dict, client: Any) -> dict:
    response = client.system_one(state=build_state(issue), questions=QUESTIONS)
    usage = response.usage
    return {
        "answers": serialize_answers(response),
        "tokens": (usage.input_tokens or 0) + (usage.output_tokens or 0),
        "model": response.model,
    }


def classify_many(issues: list[dict], client: Any) -> tuple[dict[int, dict], list[int]]:
    """Classify issues concurrently. Returns ({issue_id: result}, [failed_issue_ids])."""

    def one(issue: dict) -> tuple[int, dict | None]:
        try:
            return issue["id"], classify_issue(issue, client)
        except TypeSafeError as exc:  # one bad call must not sink the whole run
            print(f"classify failed for #{issue['number']}: {type(exc).__name__}")
            return issue["id"], None

    results: dict[int, dict] = {}
    failed: list[int] = []
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
        for issue_id, result in pool.map(one, issues):
            if result is None:
                failed.append(issue_id)
            else:
                results[issue_id] = result
    return results, failed
