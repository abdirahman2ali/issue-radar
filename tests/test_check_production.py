import json
from datetime import datetime, timedelta, timezone

from scripts.check_production import check, main

NOW = datetime(2026, 11, 14, 12, 0, tzinfo=timezone.utc)
MAX_AGE = timedelta(hours=30)


def site(generated="2026-11-14T06:00:00Z", issues=(1,), status=200, extra=""):
    body = json.dumps({"generated_at": generated, "issues": list(issues)}) + extra

    def fetch(url):
        return (status, body) if url.endswith("triage.json") else (status, "<html>")

    return fetch


def test_healthy():
    assert check("https://x.dev", NOW, MAX_AGE, site()) == []


def test_stale_data():
    problems = check("https://x.dev", NOW, MAX_AGE, site(generated="2026-11-10T14:54:12Z"))
    assert any("stale" in p for p in problems)


def test_empty_issues():
    assert any("no issues" in p for p in check("https://x.dev", NOW, MAX_AGE, site(issues=())))


def test_http_error():
    problems = check("https://x.dev", NOW, MAX_AGE, site(status=503))
    assert any("503" in p for p in problems)


def test_secret_in_data():
    key = "sk-ant-api03-" + "Zy9Xw8Vu" * 4
    problems = check("https://x.dev", NOW, MAX_AGE, site(extra=f" {key}"))
    assert any("secret" in p for p in problems)


def test_unreachable():
    def boom(url):
        raise OSError("down")

    problems = check("https://x.dev", NOW, MAX_AGE, boom)
    assert len(problems) == 2 and all("unreachable" in p for p in problems)


def test_https_only(capsys):
    try:
        main(["--url", "http://x.dev"])
    except SystemExit as exc:
        assert exc.code == 2
