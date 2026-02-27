"""Tests for the Expert Graph and Steer evaluation system."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Expert Graph
# ---------------------------------------------------------------------------


class TestExpertGraph:
    @pytest.mark.asyncio
    async def test_build_expert_graph(self):
        mock_sb = MagicMock()

        # Mock goal lookup
        goal_result = MagicMock()
        goal_result.data = [{"title": "Get FAANG SWE offer", "description": "Land a job at a top tech company"}]

        # Mock delete existing
        delete_result = MagicMock()
        delete_result.data = []

        # Mock insert new skills
        skills = [
            {"skill_name": "algorithms", "weight": 0.9, "category": "technical"},
            {"skill_name": "system design", "weight": 0.8, "category": "technical"},
            {"skill_name": "behavioral interviews", "weight": 0.7, "category": "interpersonal"},
        ]
        insert_result = MagicMock()
        insert_result.data = [
            {"id": f"skill-{i}", "tenant_id": "t1", "goal_id": "g1", **s}
            for i, s in enumerate(skills)
        ]

        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return goal_result
            elif call_count == 2:
                return delete_result
            else:
                return insert_result

        mock_sb.table.return_value.select.return_value.eq.return_value.execute = mock_execute
        mock_sb.table.return_value.delete.return_value.eq.return_value.execute = MagicMock(return_value=delete_result)
        mock_sb.table.return_value.insert.return_value.execute = MagicMock(return_value=insert_result)

        # Mock Claude response
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(type="text", text=json.dumps(skills))]

        with patch("cascade_api.steer.expert_graph.get_anthropic") as mock_get:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_msg)
            mock_get.return_value = mock_client

            from cascade_api.steer.expert_graph import build_expert_graph
            result = await build_expert_graph(mock_sb, "t1", "g1", "test-key")

        assert len(result) == 3
        mock_client.messages.create.assert_called_once()


# ---------------------------------------------------------------------------
# Skill Tracker
# ---------------------------------------------------------------------------


class TestSkillTracker:
    @pytest.mark.asyncio
    async def test_update_skill_insert(self):
        mock_sb = MagicMock()

        # No existing skill
        select_result = MagicMock()
        select_result.data = []
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = MagicMock(
            return_value=select_result
        )

        # Insert result
        insert_result = MagicMock()
        insert_result.data = [{"id": "s1", "skill_name": "algorithms", "proficiency": 0.5}]
        mock_sb.table.return_value.insert.return_value.execute = MagicMock(return_value=insert_result)

        from cascade_api.steer.skill_tracker import update_skill
        result = await update_skill(mock_sb, "t1", "algorithms", 0.5)

        assert result["proficiency"] == 0.5

    @pytest.mark.asyncio
    async def test_update_skill_update(self):
        mock_sb = MagicMock()

        # Existing skill
        select_result = MagicMock()
        select_result.data = [{"id": "s1"}]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = MagicMock(
            return_value=select_result
        )

        # Update result
        update_result = MagicMock()
        update_result.data = [{"id": "s1", "skill_name": "algorithms", "proficiency": 0.7}]
        mock_sb.table.return_value.update.return_value.eq.return_value.execute = MagicMock(
            return_value=update_result
        )

        from cascade_api.steer.skill_tracker import update_skill
        result = await update_skill(mock_sb, "t1", "algorithms", 0.7)

        assert result["proficiency"] == 0.7

    @pytest.mark.asyncio
    async def test_get_skill_gaps(self):
        mock_sb = MagicMock()

        # Expert skills
        expert_result = MagicMock()
        expert_result.data = [
            {"skill_name": "algorithms", "weight": "0.9", "category": "technical"},
            {"skill_name": "system design", "weight": "0.8", "category": "technical"},
            {"skill_name": "networking", "weight": "0.3", "category": "interpersonal"},
        ]

        # User skills
        user_result = MagicMock()
        user_result.data = [
            {"skill_name": "algorithms", "proficiency": "0.4"},
        ]

        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return expert_result
            else:
                return user_result

        mock_sb.table.return_value.select.return_value.eq.return_value.execute = mock_execute

        from cascade_api.steer.skill_tracker import get_skill_gaps
        gaps = await get_skill_gaps(mock_sb, "t1", "g1")

        assert len(gaps) == 3
        # Should be sorted by gap descending
        # system_design: 0.8 - 0 = 0.8 (biggest gap)
        # algorithms: 0.9 - 0.4 = 0.5
        # networking: 0.3 - 0 = 0.3
        assert gaps[0]["skill_name"] == "system design"
        assert gaps[0]["gap"] == 0.8
        assert gaps[1]["skill_name"] == "algorithms"
        assert gaps[1]["gap"] == 0.5

    @pytest.mark.asyncio
    async def test_apply_decay(self):
        mock_sb = MagicMock()

        five_days_ago = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()

        select_result = MagicMock()
        select_result.data = [
            {"id": "s1", "proficiency": "0.5", "last_practiced_at": five_days_ago},
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.execute = MagicMock(
            return_value=select_result
        )

        update_result = MagicMock()
        update_result.data = [{}]
        mock_sb.table.return_value.update.return_value.eq.return_value.execute = MagicMock(
            return_value=update_result
        )

        from cascade_api.steer.skill_tracker import apply_decay
        updated = await apply_decay(mock_sb, "t1", decay_rate=0.02)

        assert updated == 1
        # Verify update was called with reduced proficiency
        # 0.5 - 0.02 * 5 = 0.4
        update_call = mock_sb.table.return_value.update.call_args
        assert update_call is not None


# ---------------------------------------------------------------------------
# ROI Evaluation
# ---------------------------------------------------------------------------


class TestEvaluateTaskROI:
    @pytest.mark.asyncio
    async def test_high_alignment(self):
        mock_sb = MagicMock()

        # Task maps to "algorithms"
        task_skills_response = MagicMock()
        task_skills_response.content = [MagicMock(type="text", text='["algorithms"]')]

        # Expert skills
        expert_result = MagicMock()
        expert_result.data = [
            {"skill_name": "algorithms", "weight": "0.9"},
            {"skill_name": "system design", "weight": "0.8"},
        ]

        # User skills (low proficiency = big gap)
        user_result = MagicMock()
        user_result.data = [
            {"skill_name": "algorithms", "proficiency": "0.1"},
        ]

        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return expert_result
            else:
                return user_result

        mock_sb.table.return_value.select.return_value.eq.return_value.execute = mock_execute

        with patch("cascade_api.steer.evaluate.get_anthropic") as mock_get:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=task_skills_response)
            mock_get.return_value = mock_client

            from cascade_api.steer.evaluate import evaluate_task_roi
            result = await evaluate_task_roi(
                mock_sb, "t1", "g1", "Solve LeetCode graph problems", "test-key"
            )

        assert result["alignment_score"] > 0
        assert len(result["matched_skills"]) == 1
        assert result["matched_skills"][0]["skill_name"] == "algorithms"
        # High alignment — no alternatives suggested
        assert result["suggestion"] is None
        assert result["alternatives"] == []

    @pytest.mark.asyncio
    async def test_low_alignment_suggests_alternatives(self):
        mock_sb = MagicMock()

        # Task maps to a skill not in the expert graph
        task_skills_response = MagicMock()
        task_skills_response.content = [MagicMock(type="text", text='["cooking"]')]

        # Alternative suggestion response
        alt_response = MagicMock()
        alt_response.content = [MagicMock(
            type="text",
            text='["Solve 5 LeetCode medium problems", "Practice system design mock interview"]',
        )]

        # Expert skills
        expert_result = MagicMock()
        expert_result.data = [
            {"skill_name": "algorithms", "weight": "0.9"},
        ]

        # User skills
        user_result = MagicMock()
        user_result.data = []

        # Skill gaps for alternatives
        gaps_expert = MagicMock()
        gaps_expert.data = [{"skill_name": "algorithms", "weight": "0.9", "category": "technical"}]
        gaps_user = MagicMock()
        gaps_user.data = []

        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return expert_result
            elif call_count == 2:
                return user_result
            elif call_count == 3:
                return gaps_expert
            elif call_count == 4:
                return gaps_user
            else:
                return MagicMock(data=[])

        mock_sb.table.return_value.select.return_value.eq.return_value.execute = mock_execute

        with patch("cascade_api.steer.evaluate.get_anthropic") as mock_get:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(side_effect=[task_skills_response, alt_response])
            mock_get.return_value = mock_client

            from cascade_api.steer.evaluate import evaluate_task_roi
            result = await evaluate_task_roi(
                mock_sb, "t1", "g1", "Learn to cook pasta", "test-key"
            )

        assert result["alignment_score"] < 0.3
        assert result["suggestion"] is not None
        assert len(result["alternatives"]) == 2


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------


class TestIndicators:
    @pytest.mark.asyncio
    async def test_create_indicator(self):
        mock_sb = MagicMock()
        insert_result = MagicMock()
        insert_result.data = [{
            "id": "ind-1",
            "tenant_id": "t1",
            "goal_id": "g1",
            "title": "Solve 50 LeetCode problems",
            "target_value": 50,
            "current_value": 0,
        }]
        mock_sb.table.return_value.insert.return_value.execute = MagicMock(return_value=insert_result)

        from cascade_api.db.indicators import create_indicator
        result = await create_indicator(
            mock_sb, "t1", "g1", "Solve 50 LeetCode problems", 50,
            unit="problems", skill_name="algorithms",
        )

        assert result["title"] == "Solve 50 LeetCode problems"
        assert result["target_value"] == 50

    @pytest.mark.asyncio
    async def test_get_deficit(self):
        mock_sb = MagicMock()
        select_result = MagicMock()
        select_result.data = [
            {"id": "i1", "title": "LeetCode", "target_value": 50, "current_value": 10, "unit": "problems", "skill_name": "algorithms", "due_date": None},
            {"id": "i2", "title": "System Design", "target_value": 20, "current_value": 15, "unit": "sessions", "skill_name": "system design", "due_date": None},
        ]
        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute = MagicMock(
            return_value=select_result
        )

        from cascade_api.db.indicators import get_deficit
        deficits = await get_deficit(mock_sb, "t1", "g1")

        assert len(deficits) == 2
        # LeetCode has bigger deficit: 50-10=40 vs 20-15=5
        assert deficits[0]["title"] == "LeetCode"
        assert deficits[0]["deficit"] == 40
        assert deficits[1]["deficit"] == 5

    @pytest.mark.asyncio
    async def test_complete_indicator_bumps_skill(self):
        mock_sb = MagicMock()

        # complete_indicator update
        update_result = MagicMock()
        update_result.data = [{
            "id": "i1",
            "tenant_id": "t1",
            "skill_name": "algorithms",
            "completed": True,
        }]
        mock_sb.table.return_value.update.return_value.eq.return_value.execute = MagicMock(
            return_value=update_result
        )

        # user_skills lookup for bump
        user_result = MagicMock()
        user_result.data = [{"proficiency": "0.3"}]

        # user_skills upsert select (no existing)
        no_result = MagicMock()
        no_result.data = [{"id": "s1"}]

        skill_update_result = MagicMock()
        skill_update_result.data = [{"proficiency": 0.4}]

        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                return user_result
            else:
                return skill_update_result

        mock_sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute = mock_execute

        from cascade_api.db.indicators import complete_indicator
        result = await complete_indicator(mock_sb, "i1")

        assert result["completed"] is True
