import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from pipeline.config import EXCERPT_CHARS, MAX_ISSUES, MODEL, WINDOW_DAYS

Classifier = Callable[[list[dict]], tuple[dict[int, dict], list[int]]]


def parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def fmt_ts(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def record_key(repo: str, number: int) -> str:
    return f"{repo}#{number}"


def complete_days(now: datetime) -> dict[str, str]:
    """First and last UTC calendar day that the window covers in full.

    Today is still filling up, and the oldest day starts part way through (the window opens at
    the time of day the job runs), so both are left out. The site shows only these days.
    """
    now = now.astimezone(timezone.utc)
    first = (now - timedelta(days=WINDOW_DAYS)).date() + timedelta(days=1)
    last = now.date() - timedelta(days=1)
    return {"from": first.isoformat(), "through": last.isoformat()}


def excerpt(body: str | None) -> str:
    text = re.sub(r"\s+", " ", body or "").strip()
    return text[:EXCERPT_CHARS]


def safe_issue_url(url: str | None) -> str:
    """Keep only https://github.com links so the site can never render a foreign href."""
    parts = urlparse(url or "")
    return url if parts.scheme == "https" and parts.hostname == "github.com" else ""


def github_fields(repo: str, issue: dict) -> dict:
    return {
        "repo": repo,
        "number": issue["number"],
        "title": issue["title"],
        "url": safe_issue_url(issue.get("html_url")),
        "author": (issue.get("user") or {}).get("login"),
        "state": issue["state"],
        "labels": [lbl["name"] for lbl in issue.get("labels", []) if isinstance(lbl, dict)],
        "comments": issue.get("comments", 0),
        "created_at": issue["created_at"],
        "updated_at": issue["updated_at"],
        "excerpt": excerpt(issue.get("body")),
    }


def empty_state() -> dict:
    return {"generated_at": None, "watermark": None, "model": MODEL, "issues": []}


def update_state(
    state: dict,
    fetched: list[tuple[str, dict]],
    classify: Classifier,
    now: datetime,
    since: datetime,
    limit: int | None = None,
    eligible_after: datetime | None = None,
) -> tuple[dict, dict]:
    """Merge freshly fetched issues into state. Returns (new_state, stats).

    Known issues only get their GitHub fields refreshed. New issues are classified once, and
    only if created inside the window (and after `eligible_after`, used to keep the first
    backfill short). The watermark advances to `now` only when every new issue was
    classified, so a failed or limited run is retried from the same point next time.
    """
    by_key = {record_key(r["repo"], r["number"]): r for r in state["issues"]}
    cutoff = now - timedelta(days=WINDOW_DAYS)
    new_cutoff = max(cutoff, eligible_after) if eligible_after else cutoff

    new_items: list[tuple[str, dict]] = []
    refreshed = 0
    for repo, issue in fetched:
        key = record_key(repo, issue["number"])
        if key in by_key:
            by_key[key].update(github_fields(repo, issue))
            refreshed += 1
        elif parse_ts(issue["created_at"]) >= new_cutoff:
            new_items.append((repo, issue))

    new_items.sort(key=lambda p: p[1]["created_at"], reverse=True)
    truncated = limit is not None and len(new_items) > limit
    batch = new_items[:limit] if limit is not None else new_items

    results, failed = classify([issue for _, issue in batch])
    classified_at = fmt_ts(now)
    tokens = 0
    for repo, issue in batch:
        result = results.get(issue["id"])
        if result is None:
            continue
        tokens += result["tokens"]
        by_key[record_key(repo, issue["number"])] = {
            **github_fields(repo, issue),
            "answers": result["answers"],
            "model": result["model"],
            "classified_at": classified_at,
        }

    kept = [r for r in by_key.values() if parse_ts(r["created_at"]) >= cutoff]
    kept.sort(key=lambda r: r["created_at"], reverse=True)
    kept = kept[:MAX_ISSUES]

    complete = not failed and not truncated
    new_state: dict[str, Any] = {
        "generated_at": classified_at,
        "watermark": fmt_ts(now) if complete else (state.get("watermark") or fmt_ts(since)),
        "model": state.get("model", MODEL),
        "complete_days": complete_days(now),
        "issues": kept,
    }
    stats = {
        "fetched": len(fetched),
        "refreshed": refreshed,
        "new": len(new_items),
        "classified": len(results),
        "failed": len(failed),
        "tokens": tokens,
        "kept": len(kept),
        "complete": complete,
    }
    return new_state, stats


def reclassify_state(
    state: dict,
    fetched: list[tuple[str, dict]],
    classify: Classifier,
    now: datetime,
    names: list[str],
) -> tuple[dict, dict]:
    """Re-ask Jev the `names` questions for known issues and overwrite only those answers.

    Everything else on the record is kept. The watermark is left alone, so the next normal run
    still picks up new issues. Each overwritten question is stamped with the time and the model
    that answered it, so mixed history stays traceable.
    """
    by_key = {record_key(r["repo"], r["number"]): r for r in state["issues"]}
    targets = [(repo, i) for repo, i in fetched if record_key(repo, i["number"]) in by_key]
    results, failed = classify([issue for _, issue in targets])

    ts = fmt_ts(now)
    tokens = 0
    for repo, issue in targets:
        result = results.get(issue["id"])
        if result is None:
            continue
        record = by_key[record_key(repo, issue["number"])]
        record["answers"].update({n: result["answers"][n] for n in names})
        stamp = {"at": ts, "model": result["model"]}
        record.setdefault("reclassified", {}).update({n: stamp for n in names})
        tokens += result["tokens"]

    fetched_keys = {record_key(repo, i["number"]) for repo, i in fetched}
    new_state = {
        **state,
        "generated_at": ts,
        "complete_days": complete_days(now),
        "issues": list(by_key.values()),
    }
    stats = {
        "reclassified": len(results),
        "failed": len(failed),
        "not_fetched": len(by_key.keys() - fetched_keys),
        "tokens": tokens,
    }
    return new_state, stats
