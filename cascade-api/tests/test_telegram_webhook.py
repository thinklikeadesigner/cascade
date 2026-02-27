"""Tests for the Telegram webhook endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_bot_app():
    """Create a mock Telegram Application."""
    bot_app = MagicMock()
    bot_app.bot = MagicMock()
    bot_app.process_update = AsyncMock()
    return bot_app


@pytest.fixture
def client_with_secret(mock_bot_app):
    """TestClient with webhook secret configured and bot_app in app.state."""
    with (
        patch("cascade_api.dependencies.get_supabase", return_value=MagicMock()),
        patch("cascade_api.config.settings.telegram_webhook_secret", "test-secret"),
        patch("cascade_api.config.settings.telegram_bot_token", "fake-token"),
    ):
        from cascade_api.main import app
        app.state.bot_app = mock_bot_app
        yield TestClient(app)


@pytest.fixture
def client_no_secret(mock_bot_app):
    """TestClient with no webhook secret configured."""
    with (
        patch("cascade_api.dependencies.get_supabase", return_value=MagicMock()),
        patch("cascade_api.config.settings.telegram_webhook_secret", ""),
        patch("cascade_api.config.settings.telegram_bot_token", "fake-token"),
    ):
        from cascade_api.main import app
        app.state.bot_app = mock_bot_app
        yield TestClient(app)


SAMPLE_UPDATE = {
    "update_id": 123456,
    "message": {
        "message_id": 1,
        "from": {"id": 999, "is_bot": False, "first_name": "Test"},
        "chat": {"id": 999, "type": "private"},
        "date": 1700000000,
        "text": "hello",
    },
}


class TestWebhookEndpoint:
    def test_valid_secret_processes_update(self, client_with_secret, mock_bot_app):
        """A request with the correct secret header should process the update."""
        with patch("cascade_api.api.telegram_webhook.Update") as MockUpdate:
            mock_update = MagicMock()
            MockUpdate.de_json.return_value = mock_update

            resp = client_with_secret.post(
                "/api/telegram/webhook",
                json=SAMPLE_UPDATE,
                headers={"X-Telegram-Bot-Api-Secret-Token": "test-secret"},
            )

            assert resp.status_code == 200
            assert resp.json() == {"ok": True}
            MockUpdate.de_json.assert_called_once_with(SAMPLE_UPDATE, mock_bot_app.bot)
            mock_bot_app.process_update.assert_called_once_with(mock_update)

    def test_invalid_secret_rejected(self, client_with_secret, mock_bot_app):
        """A request with a wrong secret header should be rejected with 401."""
        resp = client_with_secret.post(
            "/api/telegram/webhook",
            json=SAMPLE_UPDATE,
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong-secret"},
        )

        assert resp.status_code == 401
        mock_bot_app.process_update.assert_not_called()

    def test_missing_secret_header_rejected(self, client_with_secret, mock_bot_app):
        """A request without the secret header should be rejected with 401."""
        resp = client_with_secret.post(
            "/api/telegram/webhook",
            json=SAMPLE_UPDATE,
        )

        assert resp.status_code == 401
        mock_bot_app.process_update.assert_not_called()

    def test_no_secret_configured_allows_all(self, client_no_secret, mock_bot_app):
        """When no webhook secret is configured, requests are allowed without the header."""
        with patch("cascade_api.api.telegram_webhook.Update") as MockUpdate:
            mock_update = MagicMock()
            MockUpdate.de_json.return_value = mock_update

            resp = client_no_secret.post(
                "/api/telegram/webhook",
                json=SAMPLE_UPDATE,
            )

            assert resp.status_code == 200
            mock_bot_app.process_update.assert_called_once()

    def test_bot_not_initialized_returns_503(self):
        """When bot_app is None, the endpoint should return 503."""
        with (
            patch("cascade_api.dependencies.get_supabase", return_value=MagicMock()),
            patch("cascade_api.config.settings.telegram_webhook_secret", ""),
            patch("cascade_api.config.settings.telegram_bot_token", ""),
        ):
            from cascade_api.main import app
            app.state.bot_app = None

            client = TestClient(app)
            resp = client.post(
                "/api/telegram/webhook",
                json=SAMPLE_UPDATE,
            )

            assert resp.status_code == 503
