"""Shared fixtures for cascade-api tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_supabase():
    """Return a MagicMock that acts like a Supabase client."""
    sb = MagicMock()
    # Default: .table().select().eq().execute() returns empty data
    sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
    sb.table.return_value.insert.return_value.execute.return_value.data = [{}]
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
    sb.table.return_value.delete.return_value.eq.return_value.execute.return_value.data = []
    sb.rpc.return_value.execute.return_value.data = []
    return sb


@pytest.fixture
def mock_anthropic():
    """Return an AsyncMock Anthropic client."""
    client = AsyncMock()
    # Default response
    msg = MagicMock()
    msg.content = [MagicMock(type="text", text="{}")]
    client.messages.create = AsyncMock(return_value=msg)
    return client


@pytest.fixture
def app(mock_supabase):
    """Create a FastAPI TestClient with mocked Supabase."""
    with patch("cascade_api.dependencies.get_supabase", return_value=mock_supabase):
        from cascade_api.main import app
        yield TestClient(app)
