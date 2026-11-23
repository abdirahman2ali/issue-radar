"""Keeps the README's "Use the data" section true.

The README documents `triage.json` as a public interface. This test checks that the documented
fields match a synthetic sample file, that the README examples run as written, and that the
security wording is present. It makes no network calls.
"""

import copy
import io
import json
import os
import re
import runpy
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import pytest

from pipeline.merge import empty_state, github_fields, update_state

ROOT = Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
FIXTURE = ROOT / "tests" / "fixtures" / "triage_sample.json"

CHOICE_ANSWERS = ("category", "area")
FLAGS = ("is_urgent", "is_regression", "has_repro", "needs_info")
SEVERITY_KEYS = {"0", "1", "2", "3"}

ISSUE_FIELDS = {
    "repo": (str,),
    "number": (int,),
    "title": (str,),
    "url": (str,),
    "author": (str, type(None)),
    "state": (str,),
    "labels": (list,),
    "comments": (int,),
    "created_at": (str,),
    "updated_at": (str,),
    "excerpt": (str,),
    "answers": (dict,),
    "model": (str,),
    "classified_at": (str,),
}
TOP_FIELDS = {
    "generated_at": (str, type(None)),
    "watermark": (str, type(None)),
    "model": (str,),
    "issues": (list,),
}


def is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def check_probabilities(path: str, value: object, errors: list[str]) -> None:
    if not isinstance(value, dict) or not all(is_number(v) for v in value.values()):
        errors.append(f"{path}.probabilities: not a map of numbers")


def check_answers(path: str, answers: dict, errors: list[str]) -> None:
    for name in CHOICE_ANSWERS:
        ans = answers.get(name)
        if not isinstance(ans, dict) or not isinstance(ans.get("choice"), str):
            errors.append(f"{path}.{name}.choice: missing or not a string")
            continue
        if not is_number(ans.get("confidence")):
            errors.append(f"{path}.{name}.confidence: missing or not a number")
        check_probabilities(f"{path}.{name}", ans.get("probabilities"), errors)
    sev = answers.get("severity")
    if not isinstance(sev, dict) or not is_number(sev.get("score")):
        errors.append(f"{path}.severity.score: missing or not a number")
        return
    if not is_number(sev.get("confidence")):
        errors.append(f"{path}.severity.confidence: missing or not a number")
    check_probabilities(f"{path}.severity", sev.get("probabilities"), errors)
    if set(sev.get("probabilities") or {}) != SEVERITY_KEYS:
        errors.append(f"{path}.severity.probabilities: keys are not 0 to 3")
    for name in FLAGS:
        flag = answers.get(name)
        if not isinstance(flag, dict) or not is_number(flag.get("noul")):
            errors.append(f"{path}.{name}.noul: missing or not a number")


def check_document(doc: dict) -> list[str]:
    """Return every way `doc` differs from the shape the README documents."""
    errors: list[str] = []
    for name, types in TOP_FIELDS.items():
        if name not in doc:
            errors.append(f"{name}: missing")
        elif not isinstance(doc[name], types):
            errors.append(f"{name}: wrong type")
    days = doc.get("complete_days")
    if days is not None and not (
        isinstance(days, dict)
        and isinstance(days.get("from"), str)
        and isinstance(days.get("through"), str)
    ):
        errors.append("complete_days: not {from, through}")
    for n, issue in enumerate(doc.get("issues") or []):
        path = f"issues[{n}]"
        for name, types in ISSUE_FIELDS.items():
            if name not in issue:
                errors.append(f"{path}.{name}: missing")
            elif not isinstance(issue[name], types) or isinstance(issue[name], bool):
                errors.append(f"{path}.{name}: wrong type")
        if issue.get("state") not in ("open", "closed"):
            errors.append(f"{path}.state: not open or closed")
        if not all(isinstance(x, str) for x in issue.get("labels") or []):
            errors.append(f"{path}.labels: not a list of strings")
        if isinstance(issue.get("answers"), dict):
            check_answers(f"{path}.answers", issue["answers"], errors)
    return errors


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def use_the_data_section() -> str:
    text = README.read_text()
    match = re.search(r"^## Use the data\n(.*?)(?=^## )", text, re.DOTALL | re.MULTILINE)
    assert match, "README has no 'Use the data' section"
    return match.group(1)


def code_block(section: str, lang: str) -> str:
    match = re.search(rf"```{lang}\n(.*?)```", section, re.DOTALL)
    assert match, f"no {lang} example in the section"
    return match.group(1)


# --- the documented shape matches the sample -------------------------------------------------


def test_fixture_matches_documented_shape():
    assert check_document(load_fixture()) == []


def test_fixture_covers_the_nullable_and_optional_fields():
    doc = load_fixture()
    assert any(i["author"] is None for i in doc["issues"])
    assert any("reclassified" in i for i in doc["issues"])
    assert "complete_days" in doc


def test_complete_days_may_be_missing():
    doc = load_fixture()
    del doc["complete_days"]
    assert check_document(doc) == []


def test_author_may_be_null_but_not_missing():
    doc = load_fixture()
    del doc["issues"][0]["author"]
    assert check_document(doc) == ["issues[0].author: missing"]


@pytest.mark.parametrize(
    "mutate, expected",
    [
        (lambda d: d["issues"][0].pop("excerpt"), "issues[0].excerpt: missing"),
        (lambda d: d["issues"][0].update(comments="3"), "issues[0].comments: wrong type"),
        (lambda d: d["issues"][1]["answers"].pop("area"), "issues[1].answers.area.choice"),
        (lambda d: d["issues"][0]["answers"]["is_urgent"].pop("noul"), "is_urgent.noul"),
        (lambda d: d["issues"][0].update(state="merged"), "state: not open or closed"),
        (lambda d: d.pop("issues"), "issues: missing"),
    ],
)
def test_a_documented_field_going_missing_or_wrong_fails(mutate, expected):
    doc = copy.deepcopy(load_fixture())
    mutate(doc)
    assert any(expected in e for e in check_document(doc))


def test_every_checked_field_is_named_in_the_readme():
    section = use_the_data_section()
    names = set(TOP_FIELDS) | set(ISSUE_FIELDS) | {"complete_days", "reclassified"}
    names |= set(CHOICE_ANSWERS) | set(FLAGS) | {"severity", "choice", "score", "noul"}
    names |= {"confidence", "probabilities"}
    missing = sorted(n for n in names if n not in section)
    assert missing == []


# --- a record built by the real pipeline code matches the documented shape -------------------

GITHUB_FIELDS = {"repo", "number", "title", "url", "author", "state", "labels", "comments"} | {
    "created_at",
    "updated_at",
    "excerpt",
}
CLASSIFIED_FIELDS = {"answers", "model", "classified_at"}
NOW = datetime(2026, 1, 3, 6, 17, tzinfo=timezone.utc)


def raw_github_issue(login: str | None) -> dict:
    return {
        "id": 1,
        "number": 7,
        "title": "Synthetic title",
        "html_url": "https://github.com/example-org/example-repo/issues/7",
        "user": {"login": login} if login else None,
        "state": "open",
        "labels": [{"name": "bug"}],
        "comments": 2,
        "created_at": "2026-01-02T03:04:05Z",
        "updated_at": "2026-01-02T04:05:06Z",
        "body": "Synthetic body.",
    }


def build_state_through_pipeline(login: str | None) -> dict:
    """Run one issue through the real merge code, with the model's answers faked."""
    answers = load_fixture()["issues"][0]["answers"]

    def classify(issues: list[dict]) -> tuple[dict[int, dict], list[int]]:
        return {
            i["id"]: {"answers": answers, "tokens": 0, "model": "test-model-1"} for i in issues
        }, []

    state, _ = update_state(
        empty_state(), [("example-org/example-repo", raw_github_issue(login))], classify, NOW, NOW
    )
    return state


def test_github_fields_are_the_documented_ones():
    assert set(github_fields("example-org/example-repo", raw_github_issue("x"))) == GITHUB_FIELDS
    assert GITHUB_FIELDS | CLASSIFIED_FIELDS == set(ISSUE_FIELDS)


@pytest.mark.parametrize("login", ["example-user", None])
def test_a_record_built_by_the_pipeline_matches_the_documented_shape(login):
    state = build_state_through_pipeline(login)
    assert len(state["issues"]) == 1
    assert state["issues"][0]["author"] == login
    assert check_document(state) == []


# --- the README examples run as written ------------------------------------------------------


def test_python_example_runs_against_the_fixture(capsys, tmp_path):
    script = tmp_path / "example.py"
    script.write_text(code_block(use_the_data_section(), "python"))
    payload = FIXTURE.read_bytes()
    seen: list[str] = []

    def fake_urlopen(url, timeout=None):
        seen.append(url)
        assert url.startswith("https://") and timeout
        return io.BytesIO(payload)

    with mock.patch("urllib.request.urlopen", fake_urlopen):
        runpy.run_path(str(script))
    assert seen == ["https://issue-radar.dev/triage.json"]
    assert capsys.readouterr().out.strip() == "1"


def test_jq_example_runs_against_the_fixture():
    if shutil.which("jq") is None:
        assert not os.environ.get("CI"), "jq must be installed in CI"
        pytest.skip("jq is not installed")
    lines = code_block(use_the_data_section(), "sh").splitlines()
    command = shlex.split(next(ln for ln in lines if ln.startswith("jq ")))
    assert command[-1] == "triage.json"
    command[-1] = str(FIXTURE)
    out = subprocess.run(command, capture_output=True, text=True, check=True, timeout=30)
    assert out.stdout.strip() == "1"


def test_examples_stay_read_only():
    section = use_the_data_section()
    examples = code_block(section, "sh") + code_block(section, "python")
    assert not re.search(r"\|\s*(ba|z)?sh\b|\beval\b|\bos\.system\b|subprocess|http://", examples)


# --- the security wording is present ---------------------------------------------------------


def test_readme_carries_the_security_wording():
    section = use_the_data_section()
    flat = re.sub(r"\s+", " ", section)
    assert "Treat every string as untrusted" in flat
    for field in ("title", "excerpt", "labels", "author"):
        assert f"`{field}`" in flat
    assert "Do not render them as HTML" in flat
    assert "interpolate them into a shell command" in flat
    assert "LLM that has tool access" in flat
    assert "Only the current file is served" in flat
    assert "History is not kept" in flat
    assert "force-pushed" in flat
    assert "https://issue-radar.dev/triage.json" in flat


def test_readme_does_not_call_the_text_clean():
    words = re.findall(r"\b(sanitized|safe|clean)\b", use_the_data_section(), re.IGNORECASE)
    assert words == []
