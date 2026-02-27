"""Tests for Telegram bot handlers."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch


@pytest.mark.asyncio
async def test_start_command_links_telegram_to_tenant():
    """The /start command with a valid token should link the Telegram ID to the tenant."""
    mock_supabase = MagicMock()
    # verify_token returns tenant_id, then handler fetches tenant by id
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"id": "tenant-1", "user_id": "auth-123", "onboarding_status": "plan_approved"}
    ]
    mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [
        {"id": "tenant-1", "telegram_id": 12345, "onboarding_status": "tg_connected"}
    ]

    with patch("cascade_api.telegram.handlers.get_supabase", return_value=mock_supabase), \
         patch("cascade_api.telegram.handlers.verify_token", return_value="tenant-1"), \
         patch("cascade_api.telegram.handlers.track_event"):
        from cascade_api.telegram.handlers import handle_start

        update = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.first_name = "Test"
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["some-deep-link-token"]

        await handle_start(update, context)

        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "set" in call_text.lower() or "welcome" in call_text.lower()


@pytest.mark.asyncio
async def test_start_command_without_args_shows_welcome():
    """The /start command without a deep link should show a welcome message."""
    with patch("cascade_api.telegram.handlers.get_supabase"):
        from cascade_api.telegram.handlers import handle_start

        update = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.first_name = "Test"
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = []

        await handle_start(update, context)

        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "welcome" in call_text.lower()


@pytest.mark.asyncio
async def test_start_command_with_invalid_token():
    """The /start command with an invalid token should show an error."""
    mock_supabase = MagicMock()

    with patch("cascade_api.telegram.handlers.get_supabase", return_value=mock_supabase), \
         patch("cascade_api.telegram.handlers.verify_token", return_value=None):
        from cascade_api.telegram.handlers import handle_start

        update = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.first_name = "Test"
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.args = ["bad-token"]

        await handle_start(update, context)

        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "invalid" in call_text.lower() or "expired" in call_text.lower()


@pytest.mark.asyncio
async def test_message_from_unknown_user():
    """Messages from unlinked Telegram accounts should get a sign-up prompt."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []

    with patch("cascade_api.telegram.handlers.get_supabase", return_value=mock_supabase):
        from cascade_api.telegram.handlers import handle_message

        update = MagicMock()
        update.effective_user.id = 99999
        update.message.text = "hello"
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await handle_message(update, context)

        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "sign up" in call_text.lower()


@pytest.mark.asyncio
async def test_message_from_inactive_user():
    """Messages from inactive accounts (trial over, no subscription) should get a subscription prompt."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "tenant-1",
            "user_id": "auth-123",
            "telegram_id": 12345,
            "completed_weekly_reviews": 3,
            "subscription_status": "none",
        }
    ]

    with patch("cascade_api.telegram.handlers.get_supabase", return_value=mock_supabase):
        from cascade_api.telegram.handlers import handle_message

        update = MagicMock()
        update.effective_user.id = 12345
        update.message.text = "hello"
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await handle_message(update, context)

        update.message.reply_text.assert_called_once()
        call_text = update.message.reply_text.call_args[0][0]
        assert "trial" in call_text.lower() or "subscription" in call_text.lower()


@pytest.mark.asyncio
async def test_status_message_triggers_status_handler():
    """Sending 'status' should trigger the status handler."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "tenant-1",
            "user_id": "auth-123",
            "telegram_id": 12345,
            "completed_weekly_reviews": 0,
            "subscription_status": "none",
        }
    ]

    with (
        patch("cascade_api.telegram.handlers.get_supabase", return_value=mock_supabase),
        patch("cascade_api.telegram.handlers._handle_status", new_callable=AsyncMock) as mock_status,
    ):
        from cascade_api.telegram.handlers import handle_message

        update = MagicMock()
        update.effective_user.id = 12345
        update.message.text = "status"
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await handle_message(update, context)

        mock_status.assert_called_once()


@pytest.mark.asyncio
async def test_log_message_triggers_log_handler():
    """Sending a regular message should trigger the log handler."""
    mock_supabase = MagicMock()
    mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {
            "id": "tenant-1",
            "user_id": "auth-123",
            "telegram_id": 12345,
            "completed_weekly_reviews": 0,
            "subscription_status": "none",
        }
    ]

    with (
        patch("cascade_api.telegram.handlers.get_supabase", return_value=mock_supabase),
        patch("cascade_api.telegram.handlers._handle_log", new_callable=AsyncMock) as mock_log,
    ):
        from cascade_api.telegram.handlers import handle_message

        update = MagicMock()
        update.effective_user.id = 12345
        update.message.text = "sent 5 DMs today, energy was high"
        update.message.reply_text = AsyncMock()

        context = MagicMock()

        await handle_message(update, context)

        mock_log.assert_called_once()
