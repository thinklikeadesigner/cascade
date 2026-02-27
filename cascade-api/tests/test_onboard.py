"""Tests for onboarding API endpoints.

These tests verify the onboard module logic in isolation, without importing
the full app (which pulls in langgraph and other heavy dependencies).
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_supabase_mock(*, tenant_exists: bool = False):
    """Build a mock Supabase client with configurable tenant lookup behavior."""
    sb = MagicMock()

    existing_tenant = {"id": "tenant-1", "onboarding_status": "signed_up"} if tenant_exists else None
    created_tenant = {"id": "tenant-1", "onboarding_status": "goal_set"}
    created_goal = {"id": "goal-1", "tenant_id": "tenant-1", "title": "Run a marathon"}

    def table_side_effect(table_name):
        mock_table = MagicMock()
        if table_name == "tenants":
            if existing_tenant:
                mock_table.select.return_value.eq.return_value.execute.return_value.data = [existing_tenant]
            else:
                mock_table.select.return_value.eq.return_value.execute.return_value.data = []
            mock_table.insert.return_value.execute.return_value.data = [created_tenant]
            mock_table.update.return_value.eq.return_value.execute.return_value.data = [created_tenant]
        elif table_name == "goals":
            mock_table.insert.return_value.execute.return_value.data = [created_goal]
        return mock_table

    sb.table.side_effect = table_side_effect
    return sb


@pytest.fixture()
def onboard_app():
    """Create a minimal FastAPI app with only the onboard router mounted."""
    with patch("cascade_api.api.onboard.track_event") as mock_track:
        from cascade_api.api.onboard import router
        app = FastAPI()
        app.include_router(router)
        yield app, mock_track


def test_create_goal_returns_goal_and_tenant(onboard_app):
    """POST /api/onboard/goal should create tenant + goal and return both."""
    app, _ = onboard_app
    mock_supabase = _make_supabase_mock(tenant_exists=False)

    with patch("cascade_api.api.onboard.get_supabase", return_value=mock_supabase):
        client = TestClient(app)
        response = client.post("/api/onboard/goal", json={
            "user_id": "auth-user-123",
            "title": "Run a marathon",
            "description": "Complete a full 26.2 mile marathon",
            "success_criteria": "Finish under 4 hours",
            "target_date": "2026-10-01",
            "current_state": "Can run 5K",
            "core_hours": 8,
            "flex_hours": 4,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-1"
        assert data["goal_id"] == "goal-1"
        assert data["status"] == "goal_set"


def test_create_goal_reuses_existing_tenant(onboard_app):
    """POST /api/onboard/goal should reuse an existing tenant."""
    app, _ = onboard_app
    mock_supabase = _make_supabase_mock(tenant_exists=True)

    with patch("cascade_api.api.onboard.get_supabase", return_value=mock_supabase):
        client = TestClient(app)
        response = client.post("/api/onboard/goal", json={
            "user_id": "auth-user-123",
            "title": "Run a marathon",
            "description": "Complete a full 26.2 mile marathon",
            "success_criteria": "Finish under 4 hours",
            "target_date": "2026-10-01",
            "current_state": "Can run 5K",
            "core_hours": 8,
            "flex_hours": 4,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["tenant_id"] == "tenant-1"


def test_connect_telegram_success(onboard_app):
    """POST /api/onboard/connect-telegram should link telegram_id to tenant."""
    app, _ = onboard_app
    mock_supabase = _make_supabase_mock(tenant_exists=True)

    with patch("cascade_api.api.onboard.get_supabase", return_value=mock_supabase):
        client = TestClient(app)
        response = client.post("/api/onboard/connect-telegram", json={
            "user_id": "auth-user-123",
            "telegram_id": 123456789,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "tg_connected"
        assert data["tenant_id"] == "tenant-1"


def test_connect_telegram_tenant_not_found(onboard_app):
    """POST /api/onboard/connect-telegram should 404 if tenant doesn't exist."""
    app, _ = onboard_app
    mock_supabase = _make_supabase_mock(tenant_exists=False)

    with patch("cascade_api.api.onboard.get_supabase", return_value=mock_supabase):
        client = TestClient(app)
        response = client.post("/api/onboard/connect-telegram", json={
            "user_id": "nonexistent-user",
            "telegram_id": 123456789,
        })
        assert response.status_code == 404
        assert response.json()["detail"] == "Tenant not found"


def test_create_goal_tracks_posthog_event(onboard_app):
    """POST /api/onboard/goal should track a PostHog event."""
    app, mock_track = onboard_app
    mock_supabase = _make_supabase_mock(tenant_exists=False)

    with patch("cascade_api.api.onboard.get_supabase", return_value=mock_supabase):
        client = TestClient(app)
        client.post("/api/onboard/goal", json={
            "user_id": "auth-user-123",
            "title": "Run a marathon",
            "description": "Complete a full 26.2 mile marathon",
            "success_criteria": "Finish under 4 hours",
            "target_date": "2026-10-01",
            "current_state": "Can run 5K",
            "core_hours": 8,
            "flex_hours": 4,
        })
        mock_track.assert_called_once_with(
            "auth-user-123", "goal_defined", {"goal_title": "Run a marathon"}
        )
