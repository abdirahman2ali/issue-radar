"""Check that the live site and its data look healthy. Exit 0 if so, 1 with reasons if not.

usage: python scripts/check_production.py [--url https://issue-radar.dev] [--max-age-hours 30]

Stdlib only, so it runs anywhere without installing the project.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

# Mirrors pipeline.merge.SECRET_RE. Kept separate so this script stays standalone.
SECRET_RE = re.compile(
    r"sk-ant-[A-Za-z0-9_\-]{8,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
)

Fetch = Callable[[str], tuple[int, str]]


def http_get(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "issue-radar-check"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:  # a 4xx or 5xx is a result, not a crash
        return exc.code, ""


def check(base: str, now: datetime, max_age: timedelta, fetch: Fetch = http_get) -> list[str]:
    """Return a list of problems. Empty means healthy."""
    problems: list[str] = []
    base = base.rstrip("/")

    try:
        status, _ = fetch(f"{base}/")
        if status != 200:
            problems.append(f"{base}/ returned HTTP {status}")
    except OSError as exc:
        problems.append(f"{base}/ unreachable: {type(exc).__name__}")

    try:
        status, body = fetch(f"{base}/triage.json")
    except OSError as exc:
        return problems + [f"triage.json unreachable: {type(exc).__name__}"]
    if status != 200:
        return problems + [f"triage.json returned HTTP {status}"]

    if SECRET_RE.search(body):
        problems.append("triage.json contains something that looks like a secret")
    try:
        data = json.loads(body)
        generated = datetime.fromisoformat(data["generated_at"].replace("Z", "+00:00"))
    except (ValueError, KeyError, TypeError, AttributeError):
        return problems + ["triage.json is not valid or has no generated_at"]

    age = now - generated
    if age > max_age:
        problems.append(f"data is stale: generated_at {data['generated_at']} ({age} old)")
    if not data.get("issues"):
        problems.append("triage.json has no issues")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="https://issue-radar.dev")
    parser.add_argument("--max-age-hours", type=float, default=30)
    args = parser.parse_args(argv)
    if not args.url.startswith("https://"):
        parser.error("--url must be https")

    problems = check(args.url, datetime.now(timezone.utc), timedelta(hours=args.max_age_hours))
    if problems:
        print("PRODUCTION UNHEALTHY")
        for p in problems:
            print(f"- {p}")
        return 1
    print("production healthy")
    return 0


if __name__ == "__main__":
    sys.exit(main())
