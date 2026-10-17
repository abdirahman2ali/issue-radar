import argparse
from datetime import datetime, timedelta, timezone

import pytest

from pipeline.config import BACKFILL_DAYS, WINDOW_DAYS
from pipeline.triage import resolve_since, window_days

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
