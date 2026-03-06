"""Tests for Langfuse tracing helpers."""

from unittest.mock import MagicMock, patch


def test_get_langfuse_returns_none_when_not_configured():
    """get_langfuse returns None when keys are not set."""
    with patch("cascade_api.observability.langfuse_client.settings") as mock_settings:
        mock_settings.langfuse_public_key = ""
        from cascade_api.observability.langfuse_client import get_langfuse

        get_langfuse.cache_clear()
        result = get_langfuse()
        assert result is None


def test_get_langfuse_returns_client_when_configured():
    """get_langfuse returns a Langfuse instance when keys are set."""
    mock_lf_instance = MagicMock()
    with (
        patch("cascade_api.observability.langfuse_client.settings") as mock_settings,
        patch("cascade_api.observability.langfuse_client.HAS_LANGFUSE", True),
        patch(
            "cascade_api.observability.langfuse_client.Langfuse", return_value=mock_lf_instance
        ) as mock_cls,
    ):
        mock_settings.langfuse_public_key = "pk-test"
        mock_settings.langfuse_secret_key = "sk-test"
        mock_settings.langfuse_host = "https://cloud.langfuse.com"
        from cascade_api.observability.langfuse_client import get_langfuse

        get_langfuse.cache_clear()
        result = get_langfuse()
        assert result is mock_lf_instance
        mock_cls.assert_called_once_with(
            public_key="pk-test",
            secret_key="sk-test",
            host="https://cloud.langfuse.com",
        )


def test_should_eval_skips_trivial():
    """Trivial single-word messages should not be evaluated."""
    from cascade_api.observability.langfuse_client import should_eval

    assert should_eval("status", is_scheduled=False) is False
    assert should_eval("tasks", is_scheduled=False) is False


def test_should_eval_always_evals_scheduled():
    """Scheduled messages are always evaluated."""
    from cascade_api.observability.langfuse_client import should_eval

    assert should_eval("status", is_scheduled=True) is True


def test_should_eval_samples_normal_messages():
    """Normal messages are sampled at the configured rate."""
    from cascade_api.observability.langfuse_client import should_eval

    assert (
        should_eval("Tell me about my churn signals", is_scheduled=False, sample_rate=1.0) is True
    )
    assert (
        should_eval("Tell me about my churn signals", is_scheduled=False, sample_rate=0.0) is False
    )
