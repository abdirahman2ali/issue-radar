from datetime import datetime, timezone
from types import SimpleNamespace

from pipeline.classify import classify_issue
from pipeline.config import QUESTIONS
from pipeline.merge import reclassify_state

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
REPO = "anthropics/claude-code"


def record(n: int, area: str = "other") -> dict:
    return {
        "repo": REPO,
        "number": n,
        "title": f"Issue {n}",
        "created_at": "2026-10-16T10:00:00Z",
        "answers": {
            "category": {"choice": "bug"},
            "area": {"choice": area},
            "severity": {"score": 1.0},
        },
        "model": "jev-old",
        "classified_at": "2026-10-16T11:00:00Z",
    }


def gh_issue(n: int) -> dict:
    return {"id": 1000 + n, "number": n, "title": f"Issue {n}", "body": "text"}


def fake_classify(new_area: str, fail: set[int] | None = None):
    asked: list[int] = []

    def classify(issues: list[dict]):
        results, failed = {}, []
        for issue in issues:
            asked.append(issue["number"])
            if fail and issue["number"] in fail:
                failed.append(issue["id"])
            else:
                results[issue["id"]] = {
                    "answers": {"area": {"choice": new_area}},
                    "tokens": 700,
                    "model": "jev-new",
                }
        return results, failed

    return classify, asked


def test_overwrites_only_the_named_answer():
    state = {"watermark": "2026-10-17T06:00:00Z", "issues": [record(1), record(2, "cli_terminal")]}
    classify, asked = fake_classify("desktop_app")
    new_state, stats = reclassify_state(
        state, [(REPO, gh_issue(1)), (REPO, gh_issue(2))], classify, NOW, ["area"]
    )
    by_n = {r["number"]: r for r in new_state["issues"]}
    assert sorted(asked) == [1, 2]
    assert by_n[1]["answers"]["area"]["choice"] == "desktop_app"
    assert by_n[1]["answers"]["category"] == {"choice": "bug"}
    assert by_n[1]["answers"]["severity"] == {"score": 1.0}
    assert by_n[1]["model"] == "jev-old"
    assert by_n[1]["reclassified"]["area"] == {"at": "2026-10-17T12:00:00Z", "model": "jev-new"}
    assert stats == {"reclassified": 2, "failed": 0, "not_fetched": 0, "tokens": 1400}


def test_watermark_is_untouched_and_unknown_issues_are_ignored():
    state = {"watermark": "2026-10-17T06:00:00Z", "issues": [record(1)]}
    classify, asked = fake_classify("web_cloud")
    new_state, stats = reclassify_state(
        state, [(REPO, gh_issue(1)), (REPO, gh_issue(99))], classify, NOW, ["area"]
    )
    assert asked == [1]
    assert new_state["watermark"] == "2026-10-17T06:00:00Z"
    assert [r["number"] for r in new_state["issues"]] == [1]
    assert stats["reclassified"] == 1


def test_failed_calls_keep_the_old_answer():
    state = {"watermark": None, "issues": [record(1), record(2)]}
    classify, _ = fake_classify("desktop_app", fail={2})
    new_state, stats = reclassify_state(
        state, [(REPO, gh_issue(1)), (REPO, gh_issue(2))], classify, NOW, ["area"]
    )
    by_n = {r["number"]: r for r in new_state["issues"]}
    assert by_n[1]["answers"]["area"]["choice"] == "desktop_app"
    assert by_n[2]["answers"]["area"]["choice"] == "other"
    assert "reclassified" not in by_n[2]
    assert stats["failed"] == 1


def test_issues_missing_from_the_fetch_are_counted():
    state = {"watermark": None, "issues": [record(1), record(2)]}
    classify, _ = fake_classify("desktop_app")
    _, stats = reclassify_state(state, [(REPO, gh_issue(1))], classify, NOW, ["area"])
    assert stats["not_fetched"] == 1


def test_classify_issue_can_ask_a_single_question():
    seen: dict = {}

    class Client:
        def system_one(self, state, questions):
            seen["questions"] = list(questions)
            answers = {
                name: SimpleNamespace(type="choice", choice="bug", confidence=1.0, probabilities={})
                for name in questions
            }
            usage = SimpleNamespace(input_tokens=10, output_tokens=2)
            return SimpleNamespace(answers=answers, usage=usage, model="jev-x")

    classify_issue(gh_issue(1), Client(), ["area"])
    assert seen["questions"] == ["area"]
    classify_issue(gh_issue(1), Client())
    assert seen["questions"] == list(QUESTIONS)


def test_area_taxonomy_has_the_new_buckets():
    area = QUESTIONS["area"].criteria
    for key in ("desktop_app", "model_behavior", "web_cloud", "install_update", "other"):
        assert key in area
