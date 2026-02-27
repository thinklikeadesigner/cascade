"""Tests for pull-based scheduled Telegram messages."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo


# ── Message builder tests (unchanged business logic) ───────────────


@pytest.mark.asyncio
async def test_morning_message_includes_core_excludes_flex():
    """Morning message should include Core tasks and exclude Flex tasks."""
    today = date(2026, 2, 26)  # Thursday

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value \
        .eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "title": "Send outreach",
                "category": "core",
                "completed": False,
                "scheduled_day": today.isoformat(),
                "estimated_minutes": 60,
            },
            {
                "title": "Draft spec",
                "category": "core",
                "completed": False,
                "scheduled_day": today.isoformat(),
                "estimated_minutes": 30,
            },
            {
                "title": "Research competitors",
                "category": "flex",
                "completed": False,
                "scheduled_day": today.isoformat(),
            },
            {
                "title": "Tomorrow core task",
                "category": "core",
                "completed": False,
                "scheduled_day": (today + timedelta(days=1)).isoformat(),
            },
        ]

    with patch("cascade_api.telegram.scheduler.get_supabase", return_value=mock_supabase):
        from cascade_api.telegram.scheduler import build_morning_message

        msg = await build_morning_message("tenant-1", today)

    assert "Send outreach" in msg
    assert "Draft spec" in msg
    assert "(60 min)" in msg
    assert "(30 min)" in msg
    assert "Research competitors" in msg
    assert "Flex if you have energy" in msg
    assert "Tomorrow core task" not in msg
    assert "2 Core tasks" in msg


@pytest.mark.asyncio
async def test_morning_message_no_tasks():
    """Morning message handles no tasks gracefully."""
    today = date(2026, 2, 26)

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value \
        .eq.return_value.eq.return_value.execute.return_value.data = []

    with patch("cascade_api.telegram.scheduler.get_supabase", return_value=mock_supabase):
        from cascade_api.telegram.scheduler import build_morning_message

        msg = await build_morning_message("tenant-1", today)

    assert "no Core tasks scheduled" in msg


@pytest.mark.asyncio
async def test_morning_message_excludes_completed_tasks():
    """Completed Core tasks should not appear in morning message."""
    today = date(2026, 2, 26)

    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value \
        .eq.return_value.eq.return_value.execute.return_value.data = [
            {
                "title": "Already done",
                "category": "core",
                "completed": True,
                "scheduled_day": today.isoformat(),
            },
            {
                "title": "Still pending",
                "category": "core",
                "completed": False,
                "scheduled_day": today.isoformat(),
            },
        ]

    with patch("cascade_api.telegram.scheduler.get_supabase", return_value=mock_supabase):
        from cascade_api.telegram.scheduler import build_morning_message

        msg = await build_morning_message("tenant-1", today)

    assert "Already done" not in msg
    assert "Still pending" in msg
    assert "1 Core task:" in msg


@pytest.mark.asyncio
async def test_evening_message():
    """Evening message is a simple check-in."""
    from cascade_api.telegram.scheduler import build_evening_message

    msg = await build_evening_message()
    assert msg == "How'd today go?"


# ── Timezone window tests ──────────────────────────────────────────


def test_in_window_inside():
    """Time inside the window returns True."""
    from cascade_api.telegram.scheduler import _in_window

    # 7:15 AM local — inside morning window (7:00-7:30)
    local_now = datetime(2026, 2, 26, 7, 15, tzinfo=ZoneInfo("America/New_York"))
    assert _in_window(local_now, (7, 0, 7, 30)) is True


def test_in_window_outside():
    """Time outside the window returns False."""
    from cascade_api.telegram.scheduler import _in_window

    # 8:00 AM local — outside morning window
    local_now = datetime(2026, 2, 26, 8, 0, tzinfo=ZoneInfo("America/New_York"))
    assert _in_window(local_now, (7, 0, 7, 30)) is False


def test_in_window_boundary_start():
    """Exact start of window is included."""
    from cascade_api.telegram.scheduler import _in_window

    local_now = datetime(2026, 2, 26, 7, 0, tzinfo=ZoneInfo("America/New_York"))
    assert _in_window(local_now, (7, 0, 7, 30)) is True


def test_in_window_boundary_end():
    """Exact end of window is excluded."""
    from cascade_api.telegram.scheduler import _in_window

    local_now = datetime(2026, 2, 26, 7, 30, tzinfo=ZoneInfo("America/New_York"))
    assert _in_window(local_now, (7, 0, 7, 30)) is False


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
async def test_send_morning_messages_respects_timezone():
    """Only sends to tenants whose local time is in the morning window."""
    # UTC time is 12:15 — that's 7:15 AM in New York, 6:15 AM in Chicago
    utc_now = datetime(2026, 2, 26, 12, 15, tzinfo=timezone.utc)

    tenants = [
        {
            "id": "t-ny",
            "telegram_id": 111,
            "user_id": "u1",
            "timezone": "America/New_York",
            "subscription_status": "active",
            "completed_weekly_reviews": 0,
        },
        {
            "id": "t-chi",
            "telegram_id": 222,
            "user_id": "u2",
            "timezone": "America/Chicago",
            "subscription_status": "active",
            "completed_weekly_reviews": 0,
        },
    ]

    mock_supabase = _make_supabase_mock(tenants)
    mock_bot = AsyncMock()

    with patch("cascade_api.telegram.scheduler.get_supabase", return_value=mock_supabase), \
         patch("cascade_api.telegram.scheduler.datetime") as mock_dt, \
         patch("cascade_api.telegram.scheduler.track_event"):
        mock_dt.now.return_value = utc_now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        from cascade_api.telegram.scheduler import send_morning_messages
        result = await send_morning_messages(mock_bot)

    # NY is in window (7:15 AM), Chicago is not (6:15 AM)
    assert result["sent"] == 1
    mock_bot.send_message.assert_called_once()
    call_kwargs = mock_bot.send_message.call_args[1]
    assert call_kwargs["chat_id"] == 111


@pytest.mark.asyncio
async def test_send_morning_messages_idempotent():
    """Calling twice doesn't double-send — message_deliveries prevents it."""
    utc_now = datetime(2026, 2, 26, 12, 15, tzinfo=timezone.utc)

    tenants = [
        {
            "id": "t-ny",
            "telegram_id": 111,
            "user_id": "u1",
            "timezone": "America/New_York",
            "subscription_status": "active",
            "completed_weekly_reviews": 0,
        },
    ]

    # Simulate already-sent record exists
    mock_supabase = _make_supabase_mock(tenants, deliveries=[{"id": 1}])
    mock_bot = AsyncMock()

    with patch("cascade_api.telegram.scheduler.get_supabase", return_value=mock_supabase), \
         patch("cascade_api.telegram.scheduler.datetime") as mock_dt, \
         patch("cascade_api.telegram.scheduler.track_event"):
        mock_dt.now.return_value = utc_now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        from cascade_api.telegram.scheduler import send_morning_messages
        result = await send_morning_messages(mock_bot)

    # Already sent — should not send again
    assert result["sent"] == 0
    mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_send_evening_messages_sends_in_window():
    """Evening message sent when tenant is in the 20:00-20:30 window."""
    # UTC 01:15 on Feb 27 = 8:15 PM ET on Feb 26
    utc_now = datetime(2026, 2, 27, 1, 15, tzinfo=timezone.utc)

    tenants = [
        {
            "id": "t-ny",
            "telegram_id": 111,
            "user_id": "u1",
            "timezone": "America/New_York",
            "subscription_status": "active",
            "completed_weekly_reviews": 0,
        },
    ]

    mock_supabase = _make_supabase_mock(tenants)
    mock_bot = AsyncMock()

    with patch("cascade_api.telegram.scheduler.get_supabase", return_value=mock_supabase), \
         patch("cascade_api.telegram.scheduler.datetime") as mock_dt, \
         patch("cascade_api.telegram.scheduler.track_event"):
        mock_dt.now.return_value = utc_now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        from cascade_api.telegram.scheduler import send_evening_messages
        result = await send_evening_messages(mock_bot)

    assert result["sent"] == 1
    mock_bot.send_message.assert_called_once_with(chat_id=111, text="How'd today go?")


@pytest.mark.asyncio
async def test_inactive_tenant_not_sent():
    """Tenants with completed trial and no subscription are skipped."""
    utc_now = datetime(2026, 2, 26, 12, 15, tzinfo=timezone.utc)

    tenants = [
        {
            "id": "t-expired",
            "telegram_id": 333,
            "user_id": "u3",
            "timezone": "America/New_York",
            "subscription_status": "none",
            "completed_weekly_reviews": 3,
        },
    ]

    mock_supabase = _make_supabase_mock(tenants)
    mock_bot = AsyncMock()

    with patch("cascade_api.telegram.scheduler.get_supabase", return_value=mock_supabase), \
         patch("cascade_api.telegram.scheduler.datetime") as mock_dt, \
         patch("cascade_api.telegram.scheduler.track_event"):
        mock_dt.now.return_value = utc_now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        from cascade_api.telegram.scheduler import send_morning_messages
        result = await send_morning_messages(mock_bot)

    assert result["sent"] == 0
    assert result["eligible"] == 0
    mock_bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_default_timezone_used_when_missing():
    """Tenants without a timezone field use America/New_York."""
    # 12:15 UTC = 7:15 AM ET — in morning window
    utc_now = datetime(2026, 2, 26, 12, 15, tzinfo=timezone.utc)

    tenants = [
        {
            "id": "t-notz",
            "telegram_id": 444,
            "user_id": "u4",
            "subscription_status": "active",
            "completed_weekly_reviews": 0,
            # No timezone field at all
        },
    ]

    mock_supabase = _make_supabase_mock(tenants)
    mock_bot = AsyncMock()

    with patch("cascade_api.telegram.scheduler.get_supabase", return_value=mock_supabase), \
         patch("cascade_api.telegram.scheduler.datetime") as mock_dt, \
         patch("cascade_api.telegram.scheduler.track_event"):
        mock_dt.now.return_value = utc_now
        mock_dt.fromisoformat = datetime.fromisoformat
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)

        from cascade_api.telegram.scheduler import send_morning_messages
        result = await send_morning_messages(mock_bot)

    # Should use default ET timezone and be in window
    assert result["sent"] == 1


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
