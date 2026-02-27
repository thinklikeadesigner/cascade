"""Tests for cascade plan generation API."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


SAMPLE_PLAN = {
    "year_plan": "Train progressively from 5K to marathon distance over 8 months",
    "quarterly_milestones": [
        {"quarter": 1, "description": "Build base fitness", "key_results": ["Run 10K comfortably"]},
        {"quarter": 2, "description": "Half marathon prep", "key_results": ["Complete half marathon"]},
    ],
    "monthly_targets": [
        {"month": 3, "targets": ["Run 3x per week", "Complete 10K distance"]},
    ],
    "weekly_tasks": {
        "core": [
            {"title": "Easy 3-mile run", "estimated_minutes": 30, "scheduled_day": "Monday"},
            {"title": "Interval training", "estimated_minutes": 45, "scheduled_day": "Wednesday"},
        ],
        "flex": [
            {"title": "Cross-training yoga", "estimated_minutes": 30},
        ],
    },
}


def _make_supabase_mock():
    """Build a mock Supabase client for cascade plan tests."""
    sb = MagicMock()

    goal_data = {
        "id": "goal-1",
        "tenant_id": "tenant-1",
        "title": "Run a marathon",
        "description": "Complete 26.2 miles\n\nCurrent state: Can run 5K",
        "success_criteria": "Finish under 4 hours",
        "target_date": "2026-10-01",
    }
    tenant_data = {"id": "tenant-1", "core_hours": 8, "flex_hours": 4}
    weekly_plan_data = {"id": "wp-1", "tenant_id": "tenant-1"}

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "goals":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [goal_data]
        elif table_name == "tenants":
            mock_table.select.return_value.eq.return_value.execute.return_value.data = [tenant_data]
            mock_table.update.return_value.eq.return_value.execute.return_value.data = [tenant_data]
        elif table_name == "quarterly_plans":
            mock_table.insert.return_value.execute.return_value.data = [{}]
        elif table_name == "monthly_plans":
            mock_table.insert.return_value.execute.return_value.data = [{}]
        elif table_name == "weekly_plans":
            mock_table.insert.return_value.execute.return_value.data = [weekly_plan_data]
        elif table_name == "tasks":
            mock_table.insert.return_value.execute.return_value.data = [{}]
        return mock_table

    sb.table.side_effect = table_side_effect
    return sb


def test_generate_cascade_returns_all_levels():
    """generate_cascade should return year, quarter, month, and week plans."""
    mock_supabase = _make_supabase_mock()

    with patch("cascade_api.api.cascade_plan.traced_ask", new_callable=AsyncMock) as mock_ask:
        mock_ask.return_value = json.dumps(SAMPLE_PLAN)

        from cascade_api.api.cascade_plan import generate_cascade

        result = asyncio.get_event_loop().run_until_complete(
            generate_cascade("tenant-1", "goal-1", "sk-test", mock_supabase)
        )

        assert "year_plan" in result
        assert "quarterly_milestones" in result
        assert "monthly_targets" in result
        assert "weekly_tasks" in result
        mock_ask.assert_called_once()


def test_generate_cascade_stores_quarterly_plans():
    """generate_cascade should insert quarterly milestones into Supabase."""
    mock_supabase = _make_supabase_mock()

    with patch("cascade_api.api.cascade_plan.traced_ask", new_callable=AsyncMock) as mock_ask:
        mock_ask.return_value = json.dumps(SAMPLE_PLAN)

        from cascade_api.api.cascade_plan import generate_cascade

        asyncio.get_event_loop().run_until_complete(
            generate_cascade("tenant-1", "goal-1", "sk-test", mock_supabase)
        )

        # Should have called table("quarterly_plans") for each milestone
        quarterly_calls = [
            call for call in mock_supabase.table.call_args_list
            if call.args == ("quarterly_plans",)
        ]
        assert len(quarterly_calls) == 2  # Two quarterly milestones in SAMPLE_PLAN


def test_generate_cascade_stores_tasks():
    """generate_cascade should insert core and flex tasks into Supabase."""
    mock_supabase = _make_supabase_mock()

    with patch("cascade_api.api.cascade_plan.traced_ask", new_callable=AsyncMock) as mock_ask:
        mock_ask.return_value = json.dumps(SAMPLE_PLAN)

        from cascade_api.api.cascade_plan import generate_cascade

        asyncio.get_event_loop().run_until_complete(
            generate_cascade("tenant-1", "goal-1", "sk-test", mock_supabase)
        )

        # Should have called table("tasks") for each task (2 core + 1 flex = 3)
        task_calls = [
            call for call in mock_supabase.table.call_args_list
            if call.args == ("tasks",)
        ]
        assert len(task_calls) == 3


def test_generate_cascade_updates_onboarding_status():
    """generate_cascade should set tenant onboarding_status to plan_approved."""
    mock_supabase = _make_supabase_mock()

    with (
        patch("cascade_api.api.cascade_plan.traced_ask", new_callable=AsyncMock) as mock_ask,
        patch("cascade_api.api.cascade_plan.track_event") as mock_track,
    ):
        mock_ask.return_value = json.dumps(SAMPLE_PLAN)

        from cascade_api.api.cascade_plan import generate_cascade

        asyncio.get_event_loop().run_until_complete(
            generate_cascade("tenant-1", "goal-1", "sk-test", mock_supabase)
        )

        mock_track.assert_called_once_with("tenant-1", "plan_approved", {"goal_id": "goal-1"})


@pytest.mark.skipif(
    __import__("sys").version_info < (3, 10),
    reason="Full app import requires Python 3.10+ (langgraph/state uses str | None syntax)",
)
def test_generate_plan_endpoint_returns_200():
    """POST /api/onboard/generate-plan should return 200 with the plan."""
    mock_supabase = _make_supabase_mock()

    with (
        patch("cascade_api.dependencies.get_supabase", return_value=mock_supabase),
        patch("cascade_api.api.cascade_plan.get_supabase", return_value=mock_supabase),
        patch("cascade_api.api.cascade_plan.traced_ask", new_callable=AsyncMock) as mock_ask,
        patch("cascade_api.api.cascade_plan.track_event"),
    ):
        mock_ask.return_value = json.dumps(SAMPLE_PLAN)

        from cascade_api.main import app
        from fastapi.testclient import TestClient

        client = TestClient(app)
        response = client.post("/api/onboard/generate-plan", json={
            "tenant_id": "tenant-1",
            "goal_id": "goal-1",
            "api_key": "sk-test",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "plan_approved"
        assert "plan" in data
        assert data["plan"]["year_plan"] == SAMPLE_PLAN["year_plan"]
