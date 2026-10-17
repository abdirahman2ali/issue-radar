import os
import subprocess
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


def fetch_issues(repo: str, since: datetime, client: httpx.Client) -> list[dict]:
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
        resp = client.get(url, params=params)
        resp.raise_for_status()
        issues.extend(i for i in resp.json() if "pull_request" not in i)
        url = resp.links.get("next", {}).get("url")
        params = None
    return issues


def make_client(token: str | None) -> httpx.Client:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(headers=headers, timeout=30.0, follow_redirects=True)
