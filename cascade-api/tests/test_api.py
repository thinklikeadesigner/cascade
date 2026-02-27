"""Tests for API endpoints using httpx TestClient."""

from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_supabase():
    """Supabase mock with chainable query builder."""
    sb = MagicMock()

    # Make query builders chainable
    def _chain(*args, **kwargs):
        return sb.table.return_value

    sb.table.return_value.select = MagicMock(return_value=sb.table.return_value)
    sb.table.return_value.eq = MagicMock(return_value=sb.table.return_value)
    sb.table.return_value.gte = MagicMock(return_value=sb.table.return_value)
    sb.table.return_value.lte = MagicMock(return_value=sb.table.return_value)
    sb.table.return_value.order = MagicMock(return_value=sb.table.return_value)
    sb.table.return_value.insert = MagicMock(return_value=sb.table.return_value)
    sb.table.return_value.update = MagicMock(return_value=sb.table.return_value)
    sb.table.return_value.delete = MagicMock(return_value=sb.table.return_value)

    execute_result = MagicMock()
    execute_result.data = []
    sb.table.return_value.execute = MagicMock(return_value=execute_result)

    rpc_result = MagicMock()
    rpc_result.data = []
    sb.rpc.return_value.execute = MagicMock(return_value=rpc_result)

    return sb


@pytest.fixture
def client(mock_supabase):
    """TestClient with mocked dependencies."""
    with (
        patch("cascade_api.dependencies.get_supabase", return_value=mock_supabase),
        patch("cascade_api.db.client.get_supabase", return_value=mock_supabase),
        patch("cascade_api.api.reprioritize._graph", MagicMock()),
    ):
        from cascade_api.main import app
        yield TestClient(app)


class TestHealth:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["service"] == "cascade-api"


class TestLogEndpoint:
    def test_log_success(self, client, mock_supabase):
        parsed_data = {
            "outreach_sent": 5,
            "conversations": 1,
            "energy_level": 4,
            "notes": "great call",
        }

        # Mock Claude Haiku parsing
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(type="text", text=json.dumps(parsed_data))]

        # Mock tracker entry insert
        insert_result = MagicMock()
        insert_result.data = [{"id": 1, "date": "2026-02-27", **parsed_data}]
        mock_supabase.table.return_value.execute = MagicMock(return_value=insert_result)

        # Mock conversation insert
        conv_result = MagicMock()
        conv_result.data = [{"id": 42}]
        mock_supabase.table.return_value.insert.return_value.execute = MagicMock(return_value=conv_result)

        with patch("cascade_api.api.log.get_anthropic") as mock_get:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_msg)
            mock_get.return_value = mock_client

            resp = client.post("/api/log", json={
                "tenant_id": "test-tenant",
                "text": "sent 5 DMs, had a great call, energy was high",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert "parsed" in data
        assert "conversation_id" in data


class TestStatusEndpoint:
    def test_status_no_tasks(self, client, mock_supabase):
        resp = client.get("/api/status", params={"tenant_id": "test-tenant"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["coaching_line"] == "No tasks planned this week. Run plan to generate your weekly tasks."
        assert data["rest_debt_days"] == 0

    def test_status_with_tasks(self, client, mock_supabase):
        # Mock week tasks
        tasks_data = [
            {"category": "core", "completed": True, "title": "Task 1"},
            {"category": "core", "completed": True, "title": "Task 2"},
            {"category": "core", "completed": False, "title": "Task 3"},
            {"category": "flex", "completed": False, "title": "Flex 1"},
        ]

        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            # First call is velocity, second is tasks, etc.
            if call_count == 2:
                result.data = tasks_data
            else:
                result.data = []
            return result

        mock_supabase.table.return_value.execute = mock_execute

        resp = client.get("/api/status", params={"tenant_id": "test-tenant"})
        assert resp.status_code == 200


class TestReviewEndpoint:
    def test_review_no_tasks(self, client, mock_supabase):
        resp = client.post("/api/review", json={"tenant_id": "test-tenant"})
        assert resp.status_code == 404


class TestPlanEndpoint:
    def test_plan_no_goals(self, client, mock_supabase):
        resp = client.post("/api/plan", json={
            "tenant_id": "test-tenant",
            "api_key": "test-key",
        })
        assert resp.status_code == 404
        assert "No active goals" in resp.json()["detail"]


class TestSteerEndpoint:
    def test_steer_endpoint(self, client, mock_supabase):
        task_skills = '["algorithms", "system design"]'
        mock_msg = MagicMock()
        mock_msg.content = [MagicMock(type="text", text=task_skills)]

        # Mock expert_skills query
        expert_data = MagicMock()
        expert_data.data = [
            {"skill_name": "algorithms", "weight": "0.9"},
            {"skill_name": "system design", "weight": "0.8"},
        ]
        # Mock user_skills query
        user_data = MagicMock()
        user_data.data = [
            {"skill_name": "algorithms", "proficiency": "0.3"},
        ]

        call_count = 0
        def mock_execute():
            nonlocal call_count
            call_count += 1
            result = MagicMock()
            if call_count == 1:
                result.data = expert_data.data
            elif call_count == 2:
                result.data = user_data.data
            else:
                result.data = []
            return result

        mock_supabase.table.return_value.execute = mock_execute

        with patch("cascade_api.steer.evaluate.get_anthropic") as mock_get:
            mock_client = AsyncMock()
            mock_client.messages.create = AsyncMock(return_value=mock_msg)
            mock_get.return_value = mock_client

            resp = client.post("/api/steer", json={
                "tenant_id": "test-tenant",
                "goal_id": "test-goal",
                "task_description": "Solve 10 LeetCode problems",
                "api_key": "test-key",
            })

        assert resp.status_code == 200
        data = resp.json()
        assert "alignment_score" in data
        assert "matched_skills" in data
