"""Tests for deep link token generation and verification."""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from cascade_api.telegram.tokens import generate_token, verify_token


def _mock_supabase(token_rows=None):
    """Build a mock Supabase client for token operations."""
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.return_value.data = [{}]
    sb.table.return_value.update.return_value.eq.return_value.execute.return_value.data = [{}]
    if token_rows is not None:
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = token_rows
    else:
        sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = []
    return sb


def test_generate_token_returns_url_safe_string():
    """generate_token should return a non-empty URL-safe string."""
    sb = _mock_supabase()
    token = generate_token(sb, "tenant-1")
    assert isinstance(token, str)
    assert len(token) > 20


def test_generate_token_inserts_hash_not_raw():
    """The stored value should be a SHA-256 hash, not the raw token."""
    sb = _mock_supabase()
    raw = generate_token(sb, "tenant-1")

    insert_call = sb.table.return_value.insert.call_args[0][0]
    stored_hash = insert_call["token_hash"]
    expected_hash = hashlib.sha256(raw.encode()).hexdigest()
    assert stored_hash == expected_hash
    assert stored_hash != raw


def test_generate_token_sets_expiry():
    """The inserted row should have an expires_at in the future."""
    sb = _mock_supabase()
    generate_token(sb, "tenant-1", ttl_minutes=30)

    insert_call = sb.table.return_value.insert.call_args[0][0]
    expires_at = datetime.fromisoformat(insert_call["expires_at"])
    assert expires_at > datetime.now(timezone.utc)


def test_verify_token_returns_tenant_id():
    """A valid, unused, non-expired token should return the tenant_id."""
    raw = "test-token-abc123"
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    sb = _mock_supabase(token_rows=[{
        "id": "tok-1",
        "tenant_id": "tenant-42",
        "token_hash": token_hash,
        "expires_at": expires,
        "used_at": None,
    }])

    result = verify_token(sb, raw)
    assert result == "tenant-42"


def test_verify_token_marks_as_used():
    """After verification, the token should be marked with used_at."""
    raw = "test-token-abc123"
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    sb = _mock_supabase(token_rows=[{
        "id": "tok-1",
        "tenant_id": "tenant-42",
        "token_hash": token_hash,
        "expires_at": expires,
        "used_at": None,
    }])

    verify_token(sb, raw)

    update_call = sb.table.return_value.update.call_args[0][0]
    assert "used_at" in update_call


def test_verify_token_rejects_already_used():
    """A token that was already used should return None."""
    raw = "test-token-abc123"
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

    sb = _mock_supabase(token_rows=[{
        "id": "tok-1",
        "tenant_id": "tenant-42",
        "token_hash": token_hash,
        "expires_at": expires,
        "used_at": datetime.now(timezone.utc).isoformat(),
    }])

    result = verify_token(sb, raw)
    assert result is None


def test_verify_token_rejects_expired():
    """An expired token should return None."""
    raw = "test-token-abc123"
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    sb = _mock_supabase(token_rows=[{
        "id": "tok-1",
        "tenant_id": "tenant-42",
        "token_hash": token_hash,
        "expires_at": expires,
        "used_at": None,
    }])

    result = verify_token(sb, raw)
    assert result is None


def test_verify_token_rejects_invalid():
    """A token that doesn't exist in the database should return None."""
    sb = _mock_supabase(token_rows=[])
    result = verify_token(sb, "nonexistent-token")
    assert result is None


def test_verify_token_handles_z_suffix_in_expires_at():
    """expires_at with a Z suffix (from Postgres) should parse correctly."""
    raw = "test-token-abc123"
    token_hash = hashlib.sha256(raw.encode()).hexdigest()
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    sb = _mock_supabase(token_rows=[{
        "id": "tok-1",
        "tenant_id": "tenant-42",
        "token_hash": token_hash,
        "expires_at": expires,
        "used_at": None,
    }])

    result = verify_token(sb, raw)
    assert result == "tenant-42"
