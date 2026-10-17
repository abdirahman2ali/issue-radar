import os
import subprocess
import time
from collections.abc import Callable
from datetime import datetime

import httpx

API = "https://api.github.com"


def get_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        out = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.strip() or None


RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_RETRIES = 4


def _should_retry(resp: httpx.Response) -> bool:
    if resp.status_code in RETRY_STATUSES:
        return True
    # A plain 403 is a permission error. Only retry the rate limit flavour.
    return resp.status_code == 403 and (
        "retry-after" in resp.headers or resp.headers.get("x-ratelimit-remaining") == "0"
    )


def _get(
    client: httpx.Client,
    url: str,
    params: dict | None,
    sleep: Callable[[float], None] = time.sleep,
) -> httpx.Response:
    for attempt in range(MAX_RETRIES + 1):
        resp = client.get(url, params=params)
        if not _should_retry(resp) or attempt == MAX_RETRIES:
            resp.raise_for_status()
            return resp
        retry_after = resp.headers.get("retry-after")
        sleep(float(retry_after) if retry_after else min(2.0**attempt, 30.0))
    raise AssertionError("unreachable")


def fetch_issues(
    repo: str,
    since: datetime,
    client: httpx.Client,
    sleep: Callable[[float], None] = time.sleep,
) -> list[dict]:
    """Return issues (not PRs) updated since `since`, newest activity first."""
    url: str | None = f"{API}/repos/{repo}/issues"
    params: dict | None = {
        "state": "all",
        "since": since.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sort": "updated",
        "direction": "desc",
        "per_page": 100,
    }
    issues: list[dict] = []
    while url:
        resp = _get(client, url, params, sleep)
        issues.extend(i for i in resp.json() if "pull_request" not in i)
        url = resp.links.get("next", {}).get("url")
        if url and not url.startswith(f"{API}/"):
            # Never send the bearer token anywhere but the GitHub API.
            raise ValueError("pagination link points outside api.github.com")
        params = None
    return issues


def make_client(token: str | None) -> httpx.Client:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(headers=headers, timeout=30.0, follow_redirects=True)
