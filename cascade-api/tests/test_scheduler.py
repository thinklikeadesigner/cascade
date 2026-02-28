"""Tests for pull-based scheduled Telegram messages."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


# ── Per-user schedule preference tests ────────────────────────────


def test_should_send_after_preferred_time():
    """Should send when local time is past the user's preferred time."""
    from cascade_api.telegram.scheduler import _should_send

    local_now = datetime(2026, 2, 26, 7, 15, tzinfo=ZoneInfo("America/New_York"))
    assert _should_send(local_now, 7, 0) is True


def test_should_send_before_preferred_time():
    """Should NOT send before the user's preferred time."""
    from cascade_api.telegram.scheduler import _should_send

    local_now = datetime(2026, 2, 26, 7, 15, tzinfo=ZoneInfo("America/New_York"))
    assert _should_send(local_now, 9, 0) is False


def test_should_send_exact_preferred_time():
    """Should send at exactly the preferred time."""
    from cascade_api.telegram.scheduler import _should_send

    local_now = datetime(2026, 2, 26, 9, 0, tzinfo=ZoneInfo("America/New_York"))
    assert _should_send(local_now, 9, 0) is True


def test_should_send_with_minutes():
    """Should respect minute-level preferences."""
    from cascade_api.telegram.scheduler import _should_send

    local_now = datetime(2026, 2, 26, 7, 15, tzinfo=ZoneInfo("America/New_York"))
    assert _should_send(local_now, 7, 30) is False

    local_now = datetime(2026, 2, 26, 7, 30, tzinfo=ZoneInfo("America/New_York"))
    assert _should_send(local_now, 7, 30) is True


def test_get_daily_message_type_normal():
    """Normal weekday returns 'daily'."""
    from cascade_api.telegram.scheduler import _get_daily_message_type

    # Thursday, review_day=0 (Sunday)
    today = date(2026, 2, 26)  # Thursday
    assert _get_daily_message_type(today, review_day=0) == "daily"


def test_get_daily_message_type_monday():
    """Monday returns 'monday_kickoff'."""
    from cascade_api.telegram.scheduler import _get_daily_message_type

    today = date(2026, 3, 2)  # Monday
    assert _get_daily_message_type(today, review_day=0) == "monday_kickoff"


def test_get_daily_message_type_review_day():
    """Review day returns 'weekly_review'."""
    from cascade_api.telegram.scheduler import _get_daily_message_type

    today = date(2026, 3, 1)  # Sunday
    assert _get_daily_message_type(today, review_day=0) == "weekly_review"


def test_get_daily_message_type_monday_is_review_day():
    """If review_day is Monday, Monday returns 'monday_review' (combined)."""
    from cascade_api.telegram.scheduler import _get_daily_message_type

    today = date(2026, 3, 2)  # Monday
    assert _get_daily_message_type(today, review_day=1) == "monday_review"


# ── Pull-based send tests ─────────────────────────────────────────


def _make_supabase_mock(tenants, deliveries=None):
    """Build a mock supabase client that returns different data per table."""
    if deliveries is None:
        deliveries = []

    mock = MagicMock()

    def table_router(table_name):
        chain = MagicMock()
        if table_name == "tenants":
            chain.select.return_value.not_.is_.return_value.execute.return_value.data = tenants
        elif table_name == "message_deliveries":
            # select().eq().eq().eq().execute() for _already_sent
            chain.select.return_value.eq.return_value.eq.return_value \
                .eq.return_value.execute.return_value.data = deliveries
            # insert().execute() for _record_delivery
            chain.insert.return_value.execute.return_value = MagicMock()
        elif table_name == "tasks":
            chain.select.return_value.eq.return_value.eq.return_value \
                .execute.return_value.data = []
        return chain

    mock.table.side_effect = table_router
    return mock


@pytest.mark.asyncio
async def test_send_daily_messages_respects_user_preferred_time():
    """Daily message uses per-user morning_hour/morning_minute."""
    # UTC 14:15 = 9:15 AM ET
    utc_now = datetime(2026, 2, 26, 14, 15, tzinfo=timezone.utc)

    tenants = [
        {
            "id": "t-early",
            "telegram_id": 111,
            "user_id": "u1",
            "timezone": "America/New_York",
            "subscription_status": "active",
            "completed_weekly_reviews": 0,
            "morning_hour": 7,
            "morning_minute": 0,
            "review_day": 0,
        },
        {
            "id": "t-late",
            "telegram_id": 222,
            "user_id": "u2",
            "timezone": "America/New_York",
            "subscription_status": "active",
            "completed_weekly_reviews": 0,
            "morning_hour": 10,
            "morning_minute": 0,
            "review_day": 0,
        },
    ]

    mock_supabase = _make_supabase_mock(tenants)
    mock_bot = AsyncMock()

    with patch("cascade_api.telegram.scheduler.get_supabase", return_value=mock_supabase), \
         patch("cascade_api.telegram.scheduler.datetime") as mock_dt, \
         patch("cascade_api.telegram.scheduler._build_daily_message", new_callable=AsyncMock, return_value="Your tasks today") as mock_build, \
         patch("cascade_api.telegram.scheduler.track_event"):
        mock_dt.now.return_value = utc_now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        from cascade_api.telegram.scheduler import send_daily_messages
        result = await send_daily_messages(mock_bot)

    # t-early (7 AM) should have been sent (9:15 AM > 7:00 AM)
    # t-late (10 AM) should NOT have been sent yet (9:15 AM < 10:00 AM)
    assert result["sent"] == 1
    call_kwargs = mock_bot.send_message.call_args[1]
    assert call_kwargs["chat_id"] == 111


@pytest.mark.asyncio
async def test_send_daily_messages_idempotent():
    """Calling twice doesn't double-send."""
    utc_now = datetime(2026, 2, 26, 12, 15, tzinfo=timezone.utc)

    tenants = [
        {
            "id": "t-ny",
            "telegram_id": 111,
            "user_id": "u1",
            "timezone": "America/New_York",
            "subscription_status": "active",
            "completed_weekly_reviews": 0,
            "morning_hour": 7,
            "morning_minute": 0,
            "review_day": 0,
        },
    ]

    mock_supabase = _make_supabase_mock(tenants, deliveries=[{"id": 1}])
    mock_bot = AsyncMock()

    with patch("cascade_api.telegram.scheduler.get_supabase", return_value=mock_supabase), \
         patch("cascade_api.telegram.scheduler.datetime") as mock_dt, \
         patch("cascade_api.telegram.scheduler.track_event"):
        mock_dt.now.return_value = utc_now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        from cascade_api.telegram.scheduler import send_daily_messages
        result = await send_daily_messages(mock_bot)

    assert result["sent"] == 0
    mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_trial_check_pull_idempotent():
    """Trial check doesn't re-send if delivery already recorded."""
    utc_now = datetime(2026, 2, 26, 12, 0, tzinfo=timezone.utc)

    tenants = [
        {
            "id": "t-trial",
            "telegram_id": 555,
            "user_id": "u5",
            "subscription_status": "none",
            "completed_weekly_reviews": 3,
        },
    ]

    # Already sent a trial_reminder today
    mock_supabase = _make_supabase_mock(tenants, deliveries=[{"id": 99}])
    mock_bot = AsyncMock()

    with patch("cascade_api.telegram.scheduler.get_supabase", return_value=mock_supabase), \
         patch("cascade_api.telegram.scheduler.datetime") as mock_dt, \
         patch("cascade_api.telegram.scheduler.track_event"):
        mock_dt.now.return_value = utc_now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        from cascade_api.telegram.scheduler import run_trial_check_pull
        result = await run_trial_check_pull(mock_bot)

    assert result["processed"] == 0
    mock_bot.send_message.assert_not_called()
