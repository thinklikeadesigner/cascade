import pytest
from unittest.mock import patch, MagicMock


def test_track_event_calls_posthog_capture():
    with patch("cascade_api.observability.posthog_client.get_posthog") as mock_ph:
        mock_client = MagicMock()
        mock_ph.return_value = mock_client

        from cascade_api.observability.posthog_client import track_event

        track_event(
            user_id="user-123",
            event="goal_defined",
            properties={"goal_title": "Run a marathon"},
        )

        mock_client.capture.assert_called_once_with(
            distinct_id="user-123",
            event="goal_defined",
            properties={"goal_title": "Run a marathon"},
        )
