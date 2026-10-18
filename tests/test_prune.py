from datetime import datetime, timedelta, timezone

from pipeline.config import MAX_PRUNE
from pipeline.merge import gone_issues, update_state

NOW = datetime(2026, 10, 18, 12, 0, tzinfo=timezone.utc)
SINCE = NOW - timedelta(days=2)
REPO = "anthropics/claude-code"
OTHER = "someone/else"


def record(n: int, hours_ago: float, repo: str = REPO) -> dict:
    created = (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "repo": repo,
        "number": n,
        "title": f"Issue {n}",
        "created_at": created,
        "answers": {"category": {"choice": "bug"}},
        "model": "jev",
        "classified_at": created,
    }


def gh_issue(n: int, hours_ago: float) -> dict:
    created = (NOW - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "id": 1000 + n,
        "number": n,
        "title": f"Issue {n}",
        "html_url": f"https://github.com/{REPO}/issues/{n}",
        "user": {"login": "x"},
        "state": "open",
        "labels": [],
        "comments": 0,
        "created_at": created,
        "updated_at": created,
        "body": "text",
    }


def keys(*records: dict) -> dict[str, dict]:
    return {f"{r['repo']}#{r['number']}": r for r in records}


def no_classify(batch: list[dict]):
    return {}, []


def test_a_stored_issue_missing_from_the_fetch_is_gone():
    stored = keys(record(1, 5), record(2, 5))
    assert gone_issues(stored, [(REPO, gh_issue(1, 5))], SINCE) == [f"{REPO}#2"]


def test_issues_older_than_the_fetch_start_are_left_alone():
    # Created 3 days ago, before `since`. GitHub would not return it unless it was updated.
    stored = keys(record(1, 24 * 3))
    assert gone_issues(stored, [], SINCE) == []


def test_repos_that_were_not_fetched_are_left_alone():
    stored = keys(record(1, 5), record(7, 5, repo=OTHER))
    assert gone_issues(stored, [(REPO, gh_issue(9, 1))], SINCE) == [f"{REPO}#1"]
    assert gone_issues(stored, [], SINCE, repos=[REPO]) == [f"{REPO}#1"]


def test_update_state_removes_the_deleted_issue_and_reports_it():
    state = {"watermark": None, "model": "jev", "issues": [record(1, 5), record(2, 5)]}
    new_state, stats = update_state(
        state, [(REPO, gh_issue(1, 5))], no_classify, NOW, SINCE, repos=[REPO]
    )
    assert [r["number"] for r in new_state["issues"]] == [1]
    assert stats["removed"] == 1 and stats["prune_skipped"] == 0


def test_a_mass_disappearance_is_treated_as_an_incomplete_fetch():
    count = MAX_PRUNE + 1
    state = {
        "watermark": None,
        "model": "jev",
        "issues": [record(n, 5) for n in range(1, count + 1)],
    }
    new_state, stats = update_state(state, [], no_classify, NOW, SINCE, repos=[REPO])
    assert len(new_state["issues"]) == count
    assert stats["removed"] == 0 and stats["prune_skipped"] == count


def test_the_limit_itself_still_prunes():
    state = {
        "watermark": None,
        "model": "jev",
        "issues": [record(n, 5) for n in range(1, MAX_PRUNE + 1)],
    }
    new_state, stats = update_state(state, [], no_classify, NOW, SINCE, repos=[REPO])
    assert new_state["issues"] == []
    assert stats["removed"] == MAX_PRUNE
