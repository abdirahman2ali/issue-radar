from datetime import datetime, timedelta, timezone

from pipeline.classify import build_state, serialize_answers
from pipeline.config import WINDOW_DAYS
from pipeline.merge import empty_state, safe_issue_url, update_state

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)
SINCE = NOW - timedelta(days=3)
REPO = "anthropics/claude-code"


def make_issue(number: int, hours_ago: float = 1, **over) -> dict:
    created = (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    issue = {
        "id": 1000 + number,
        "number": number,
        "title": f"Issue {number}",
        "html_url": f"https://github.com/{REPO}/issues/{number}",
        "user": {"login": "someone"},
        "state": "open",
        "labels": [{"name": "bug"}],
        "comments": 0,
        "created_at": created,
        "updated_at": created,
        "body": "Steps:\n\n1. run it\n2. it breaks",
    }
    issue.update(over)
    return issue


def fake_classifier(fail: set[int] | None = None):
    calls: list[int] = []

    def classify(issues: list[dict]):
        results, failed = {}, []
        for issue in issues:
            calls.append(issue["number"])
            if fail and issue["number"] in fail:
                failed.append(issue["id"])
            else:
                results[issue["id"]] = {
                    "answers": {"category": {"choice": "bug"}},
                    "tokens": 900,
                    "model": "jev-2026-10-01",
                }
        return results, failed

    return classify, calls


def test_new_issues_are_classified_once():
    classify, calls = fake_classifier()
    state, stats = update_state(
        empty_state(), [(REPO, make_issue(1)), (REPO, make_issue(2))], classify, NOW, SINCE
    )
    assert sorted(calls) == [1, 2]
    assert stats["classified"] == 2 and stats["tokens"] == 1800 and stats["complete"]
    assert state["watermark"] == "2026-10-17T12:00:00Z"
    assert all("answers" in r for r in state["issues"])
    assert {r["model"] for r in state["issues"]} == {"jev-2026-10-01"}

    classify2, calls2 = fake_classifier()
    state2, stats2 = update_state(state, [(REPO, make_issue(1))], classify2, NOW, SINCE)
    assert calls2 == []
    assert stats2["refreshed"] == 1 and stats2["new"] == 0
    assert len(state2["issues"]) == 2


def test_known_issue_refreshes_github_fields_but_keeps_answers():
    classify, _ = fake_classifier()
    state, _ = update_state(empty_state(), [(REPO, make_issue(1))], classify, NOW, SINCE)
    closed = make_issue(1, state="closed", comments=5, labels=[{"name": "fixed"}])
    state2, _ = update_state(state, [(REPO, closed)], classify, NOW, SINCE)
    rec = state2["issues"][0]
    assert rec["state"] == "closed" and rec["comments"] == 5 and rec["labels"] == ["fixed"]
    assert rec["answers"] == {"category": {"choice": "bug"}}


def test_window_trims_old_issues_and_skips_old_new_ones():
    classify, calls = fake_classifier()
    old = make_issue(1, hours_ago=24 * (WINDOW_DAYS + 1))
    state, _ = update_state(
        empty_state(), [(REPO, old), (REPO, make_issue(2))], classify, NOW, SINCE
    )
    assert calls == [2]
    assert [r["number"] for r in state["issues"]] == [2]


def test_failure_keeps_watermark_so_issue_is_retried():
    classify, _ = fake_classifier(fail={2})
    state, stats = update_state(
        empty_state(), [(REPO, make_issue(1)), (REPO, make_issue(2))], classify, NOW, SINCE
    )
    assert stats["failed"] == 1 and not stats["complete"]
    assert [r["number"] for r in state["issues"]] == [1]
    assert state["watermark"] == "2026-10-14T12:00:00Z"


def test_limit_classifies_newest_and_keeps_watermark():
    classify, calls = fake_classifier()
    issues = [(REPO, make_issue(n, hours_ago=n)) for n in (1, 2, 3)]
    state, stats = update_state(empty_state(), issues, classify, NOW, SINCE, limit=2)
    assert sorted(calls) == [1, 2]
    assert not stats["complete"]
    assert state["watermark"] == "2026-10-14T12:00:00Z"


def test_only_github_https_urls_are_kept():
    assert safe_issue_url("https://github.com/o/r/issues/1") == "https://github.com/o/r/issues/1"
    for bad in (
        "javascript:alert(1)",
        "http://github.com/o/r",
        "https://github.com.evil.io/x",
        None,
    ):
        assert safe_issue_url(bad) == ""


def test_build_state_truncates_body():
    issue = make_issue(1, body="x" * 5000)
    assert len(build_state(issue)) < 2100
    assert build_state(make_issue(1, body=None)) == "Title: Issue 1"


def test_serialize_answers_shapes():
    class A:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    response = A(
        answers={
            "category": A(type="choice", choice="bug", confidence=0.9, probabilities={"bug": 0.9}),
            "severity": A(type="score", score=2.4, confidence=0.7, probabilities={1: 0.1, 2: 0.9}),
            "is_urgent": A(type="noul", noul=0.2),
        }
    )
    out = serialize_answers(response)
    assert out["category"]["choice"] == "bug"
    assert out["severity"]["probabilities"] == {"1": 0.1, "2": 0.9}
    assert out["is_urgent"] == {"noul": 0.2}
