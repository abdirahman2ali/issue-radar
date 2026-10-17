from datetime import datetime, timezone

import httpx
import pytest

from pipeline.github import MAX_RETRIES, fetch_issues

SINCE = datetime(2026, 10, 14, tzinfo=timezone.utc)
NEXT_URL = "https://api.github.com/repositories/1/issues?page=2"


def client_for(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_paginates_and_drops_pull_requests():
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.params.get("page") == "2":
            return httpx.Response(200, json=[{"number": 3}])
        body = [{"number": 1}, {"number": 2, "pull_request": {"url": "x"}}]
        return httpx.Response(200, json=body, headers={"Link": f'<{NEXT_URL}>; rel="next"'})

    issues = fetch_issues("o/r", SINCE, client_for(handler), sleep=lambda _: None)
    assert [i["number"] for i in issues] == [1, 3]
    assert seen[0].url.params["since"] == "2026-10-14T00:00:00Z"
    assert seen[0].url.params["state"] == "all"


def test_rejects_pagination_link_outside_github_api():
    def handler(request: httpx.Request) -> httpx.Response:
        evil = '<https://evil.example/steal>; rel="next"'
        return httpx.Response(200, json=[{"number": 1}], headers={"Link": evil})

    with pytest.raises(ValueError):
        fetch_issues("o/r", SINCE, client_for(handler), sleep=lambda _: None)


def test_retries_server_errors_then_succeeds():
    attempts = []
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(502)
        return httpx.Response(200, json=[{"number": 1}])

    issues = fetch_issues("o/r", SINCE, client_for(handler), sleep=sleeps.append)
    assert [i["number"] for i in issues] == [1]
    assert len(attempts) == 3
    assert sleeps == [1.0, 2.0]


def test_rate_limit_403_honors_retry_after():
    attempts = []
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        if len(attempts) == 1:
            return httpx.Response(403, headers={"retry-after": "7"})
        return httpx.Response(200, json=[])

    fetch_issues("o/r", SINCE, client_for(handler), sleep=sleeps.append)
    assert sleeps == [7.0]


def test_plain_403_is_not_retried():
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(403, json={"message": "Resource not accessible"})

    with pytest.raises(httpx.HTTPStatusError):
        fetch_issues("o/r", SINCE, client_for(handler), sleep=lambda _: None)
    assert len(attempts) == 1


def test_gives_up_after_max_retries():
    attempts = []

    def handler(request: httpx.Request) -> httpx.Response:
        attempts.append(1)
        return httpx.Response(503)

    with pytest.raises(httpx.HTTPStatusError):
        fetch_issues("o/r", SINCE, client_for(handler), sleep=lambda _: None)
    assert len(attempts) == MAX_RETRIES + 1
