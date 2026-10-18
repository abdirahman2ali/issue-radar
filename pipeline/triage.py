"""Fetch new GitHub issues, classify them with Jev, and update data/triage.json."""

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from pipeline.classify import classify_many
from pipeline.config import BACKFILL_DAYS, MODEL, QUESTIONS, REPOS, WINDOW_DAYS
from pipeline.github import fetch_issues, get_token, make_client
from pipeline.merge import empty_state, fmt_ts, parse_ts, reclassify_state, update_state


def load_env() -> None:
    """Load the shared secrets file if one exists above this repo, then a local .env."""
    for parent in Path(__file__).resolve().parents:
        shared = parent / ".claude" / "credentials" / ".env"
        if shared.is_file():
            load_dotenv(shared)
            break
    load_dotenv(override=True)


def load_state(path: Path) -> dict:
    if not path.is_file():
        return empty_state()
    return json.loads(path.read_text())


def window_days(value: str) -> int:
    days = int(value)
    if not 1 <= days <= WINDOW_DAYS:
        raise argparse.ArgumentTypeError(f"must be between 1 and {WINDOW_DAYS}")
    return days


def resolve_since(
    state: dict, now: datetime, since_days: int | None
) -> tuple[datetime, datetime | None]:
    """Return (fetch_since, eligible_after) for this run.

    GitHub's `since` filters on updated time, so only a fetch that reaches back past an issue's
    creation sees it. `since_days` forces a fresh look back (a backfill) regardless of watermark.
    """
    if since_days is not None:
        return now - timedelta(days=since_days), None
    if state.get("watermark"):
        return parse_ts(state["watermark"]), None
    start = now - timedelta(days=BACKFILL_DAYS)
    return start, start


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("data/triage.json"))
    parser.add_argument("--repo", action="append", help="repo to fetch (default: config REPOS)")
    parser.add_argument("--limit", type=int, help="classify at most N new issues (testing)")
    parser.add_argument(
        "--since-days",
        type=window_days,
        help=f"re-fetch issues from the last N days (1 to {WINDOW_DAYS}), ignoring the watermark",
    )
    parser.add_argument(
        "--reclassify",
        choices=sorted(QUESTIONS),
        help="re-ask just this question for every issue in the window and overwrite its answer",
    )
    parser.add_argument("--dry-run", action="store_true", help="fetch and count, no Jev calls")
    args = parser.parse_args(argv)

    load_env()
    now = datetime.now(timezone.utc)
    state = load_state(args.out)
    state.setdefault("model", MODEL)
    since, eligible_after = resolve_since(state, now, args.since_days)
    if args.reclassify:
        # Bodies are not stored, so re-fetch the whole window to get the text again.
        since, eligible_after = now - timedelta(days=WINDOW_DAYS), None

    fetched: list[tuple[str, dict]] = []
    with make_client(get_token()) as http:
        for repo in args.repo or REPOS:
            issues = fetch_issues(repo, since, http)
            print(f"{repo}: {len(issues)} issues updated since {fmt_ts(since)}")
            fetched.extend((repo, i) for i in issues)

    if args.reclassify:
        from typesafe_sdk import TypeSafeClient

        names = [args.reclassify]
        known = {(r["repo"], r["number"]) for r in state["issues"]}
        count = sum(1 for repo, i in fetched if (repo, i["number"]) in known)
        if args.dry_run:
            print(f"dry run: would re-ask '{args.reclassify}' for {count} issues")
            return 0
        with TypeSafeClient(model=state["model"]) as jev:
            new_state, stats = reclassify_state(
                state, fetched, lambda batch: classify_many(batch, jev, names), now, names
            )
        args.out.write_text(json.dumps(new_state, indent=1))
        print(json.dumps(stats))
        return 0 if stats["failed"] == 0 else 1

    repos = args.repo or REPOS

    if args.dry_run:
        _, stats = update_state(
            state, fetched, lambda batch: ({}, []), now, since, args.limit, eligible_after, repos
        )
        print(
            f"dry run: {stats['new']} new issues would be classified, "
            f"{stats['removed']} deleted issues would be removed"
            + (
                f" ({stats['prune_skipped']} found, over the safety limit)"
                if stats["prune_skipped"]
                else ""
            )
        )
        return 0

    from typesafe_sdk import TypeSafeClient

    with TypeSafeClient(model=state["model"]) as jev:
        new_state, stats = update_state(
            state,
            fetched,
            lambda batch: classify_many(batch, jev),
            now,
            since,
            args.limit,
            eligible_after,
            repos,
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(new_state, indent=1))
    print(json.dumps(stats))
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
