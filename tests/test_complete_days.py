from datetime import date, datetime, timedelta, timezone

from pipeline.config import WINDOW_DAYS
from pipeline.merge import complete_days, empty_state, update_state

REPO = "anthropics/claude-code"


def test_excludes_today_and_the_partial_oldest_day():
    now = datetime(2026, 10, 18, 6, 17, tzinfo=timezone.utc)
    days = complete_days(now)
    assert days["through"] == "2026-10-17"
    assert days["from"] == "2026-10-11"


def test_covers_seven_complete_days_with_the_default_window():
    now = datetime(2026, 10, 18, 6, 17, tzinfo=timezone.utc)
    days = complete_days(now)
    span = date.fromisoformat(days["through"]) - date.fromisoformat(days["from"])
    assert span.days + 1 == WINDOW_DAYS - 1 == 7


def test_uses_utc_even_if_given_another_timezone():
    # 23:30 on Oct 17 in UTC-5 is already 04:30 on Oct 18 UTC.
    tz = timezone(timedelta(hours=-5))
    now = datetime(2026, 10, 17, 23, 30, tzinfo=tz)
    assert complete_days(now)["through"] == "2026-10-17"


def test_state_written_by_a_run_carries_the_field():
    now = datetime(2026, 10, 18, 6, 17, tzinfo=timezone.utc)
    state, _ = update_state(empty_state(), [], lambda batch: ({}, []), now, now - timedelta(days=1))
    assert state["complete_days"] == complete_days(now)
