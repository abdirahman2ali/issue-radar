import argparse
from datetime import datetime, timedelta, timezone

import pytest

from pipeline.config import BACKFILL_DAYS, WINDOW_DAYS
from pipeline.triage import main, requested_since_days, resolve_since, window_days

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=timezone.utc)


def test_fresh_state_backfills_the_whole_window():
    assert BACKFILL_DAYS == WINDOW_DAYS
    since, eligible_after = resolve_since({"watermark": None}, NOW, None)
    assert since == NOW - timedelta(days=WINDOW_DAYS)
    assert eligible_after == since


def test_existing_watermark_is_used_as_is():
    state = {"watermark": "2026-10-16T06:00:00Z"}
    since, eligible_after = resolve_since(state, NOW, None)
    assert since == datetime(2026, 10, 16, 6, 0, tzinfo=timezone.utc)
    assert eligible_after is None


def test_since_days_overrides_the_watermark():
    state = {"watermark": "2026-10-16T06:00:00Z"}
    since, eligible_after = resolve_since(state, NOW, 7)
    assert since == NOW - timedelta(days=7)
    assert eligible_after is None


@pytest.mark.parametrize("value", ["0", "-1", str(WINDOW_DAYS + 1)])
def test_since_days_must_stay_inside_the_window(value):
    with pytest.raises(argparse.ArgumentTypeError):
        window_days(value)


def test_since_days_accepts_window_bounds():
    assert window_days("1") == 1
    assert window_days(str(WINDOW_DAYS)) == WINDOW_DAYS


def test_full_window_is_the_max_since_days():
    assert requested_since_days(True, None) == WINDOW_DAYS
    assert requested_since_days(False, 3) == 3
    assert requested_since_days(False, None) is None
    since, eligible_after = resolve_since({"watermark": "2026-10-16T06:00:00Z"}, NOW, WINDOW_DAYS)
    assert since == NOW - timedelta(days=WINDOW_DAYS) and eligible_after is None


def test_full_window_and_since_days_cannot_be_combined():
    with pytest.raises(SystemExit):
        main(["--full-window", "--since-days", "3", "--dry-run"])
