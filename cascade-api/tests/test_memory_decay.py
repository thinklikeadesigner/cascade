"""Tests for memory decay scoring."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest


class TestCalculateDecay:
    def test_recent_memory_has_high_score(self):
        from cascade_api.agent.memory_decay import calculate_decay

        now = datetime.now(timezone.utc)
        score = calculate_decay(last_accessed=now, base_score=1.0)
        assert score > 0.99

    def test_old_memory_has_lower_score(self):
        from cascade_api.agent.memory_decay import calculate_decay

        old = datetime.now(timezone.utc) - timedelta(days=30)
        score = calculate_decay(last_accessed=old, base_score=1.0)
        assert score < 0.3

    def test_one_week_decay(self):
        from cascade_api.agent.memory_decay import calculate_decay

        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        score = calculate_decay(last_accessed=week_ago, base_score=1.0)
        # 0.95^7 ≈ 0.698
        assert 0.65 < score < 0.75


class TestUpdateDecayScores:
    @pytest.mark.asyncio
    async def test_calls_postgres_rpc(self):
        """Verify decay runs as a single Postgres RPC, not per-row Python."""
        from cascade_api.agent.memory_decay import update_decay_scores

        mock_sb = MagicMock()
        mock_sb.rpc.return_value.execute.return_value.data = 42

        result = await update_decay_scores(mock_sb)
        mock_sb.rpc.assert_called_once_with("update_memory_decay_scores", {})
        assert result == 42
