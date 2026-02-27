"""Deep link token generation and verification for secure Telegram connection."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone


def generate_token(supabase, tenant_id: str, ttl_minutes: int = 60) -> str:
    """Generate a one-time deep link token. Returns the raw token for the URL."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    supabase.table("deep_link_tokens").insert({
        "tenant_id": tenant_id,
        "token_hash": token_hash,
        "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)).isoformat(),
    }).execute()
    return raw_token


def verify_token(supabase, raw_token: str) -> str | None:
    """Verify and consume a token. Returns tenant_id or None."""
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    result = (
        supabase.table("deep_link_tokens")
        .select("*")
        .eq("token_hash", token_hash)
        .execute()
    )
    if not result.data:
        return None
    token = result.data[0]
    if token.get("used_at"):
        return None
    expires_at = token["expires_at"]
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
    if expires_at < datetime.now(timezone.utc):
        return None
    # Mark as used
    supabase.table("deep_link_tokens").update({
        "used_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", token["id"]).execute()
    return token["tenant_id"]
