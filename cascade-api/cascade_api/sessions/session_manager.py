"""Session manager — Supabase-backed session store with 24-hour expiry."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import structlog

from cascade_api.dependencies import get_supabase

log = structlog.get_logger()

TABLE = "sessions"
SESSION_EXPIRY = timedelta(hours=24)


def _is_expired(last_activity: str) -> bool:
    """Check if a session's last_activity timestamp is older than 24 hours."""
    ts = datetime.fromisoformat(last_activity)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - ts > SESSION_EXPIRY


async def create_session(thread_id: str, chat_jid: str) -> dict:
    """Create a new reprioritize session. Raises if one already exists for chat_jid."""
    existing = await get_session_by_chat_jid(chat_jid)
    if existing:
        raise ValueError(
            f"Active session already exists for {chat_jid}: {existing['thread_id']}. "
            f"Cancel it first or wait for it to complete."
        )

    now = datetime.now(timezone.utc).isoformat()
    row = {
        "thread_id": thread_id,
        "chat_jid": chat_jid,
        "started_at": now,
        "last_activity_at": now,
    }

    sb = get_supabase()
    sb.table(TABLE).insert(row).execute()

    log.info("session_created", thread_id=thread_id, chat_jid=chat_jid)
    return row


async def get_session(thread_id: str) -> dict | None:
    """Retrieve a session by thread_id. Returns None if not found or expired."""
    sb = get_supabase()
    resp = sb.table(TABLE).select("*").eq("thread_id", thread_id).execute()

    if not resp.data:
        return None

    session = resp.data[0]
    if _is_expired(session["last_activity_at"]):
        sb.table(TABLE).delete().eq("thread_id", thread_id).execute()
        log.info("session_expired", thread_id=thread_id)
        return None

    return session


async def get_session_by_chat_jid(chat_jid: str) -> dict | None:
    """Find an active (non-expired) session for a given chat_jid."""
    sb = get_supabase()
    resp = sb.table(TABLE).select("*").eq("chat_jid", chat_jid).execute()

    for session in resp.data:
        if not _is_expired(session["last_activity_at"]):
            return session

    return None


async def touch_session(thread_id: str) -> None:
    """Update the last_activity timestamp for a session."""
    sb = get_supabase()
    now = datetime.now(timezone.utc).isoformat()
    sb.table(TABLE).update({"last_activity_at": now}).eq("thread_id", thread_id).execute()


async def delete_session(thread_id: str) -> None:
    """Delete a session by thread_id."""
    sb = get_supabase()
    sb.table(TABLE).delete().eq("thread_id", thread_id).execute()
    log.info("session_deleted", thread_id=thread_id)
