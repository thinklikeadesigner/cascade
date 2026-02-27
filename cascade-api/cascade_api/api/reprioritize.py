"""API endpoints for the reverse-cascade reprioritization flow."""

from __future__ import annotations

from uuid import uuid4

import structlog
from fastapi import HTTPException
from langgraph.types import Command
from pydantic import BaseModel

from cascade_api.api.router import api_router
from cascade_api.cascade.file_writer import cleanup_backups
from cascade_api.graph.graph import build_graph
from cascade_api.sessions.session_manager import (
    create_session,
    delete_session,
    get_session,
    touch_session,
)

log = structlog.get_logger()

# Build the graph once at module level (singleton)
_graph = build_graph()


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class StartRequest(BaseModel):
    chat_jid: str
    user_request: str
    data_dir: str
    api_key: str


class RespondRequest(BaseModel):
    decision: str  # "approve" | "reject" | "stop" | "modify"
    feedback: str | None = None


class CheckpointInfo(BaseModel):
    level: str
    message: str


class StartResponse(BaseModel):
    thread_id: str
    status: str
    checkpoint: CheckpointInfo | None = None
    next: list[str] | None = None


class RespondResponse(BaseModel):
    thread_id: str
    status: str
    checkpoint: CheckpointInfo | None = None
    applied_changes: list[dict] | None = None
    next: list[str] | None = None


class StatusResponse(BaseModel):
    thread_id: str
    chat_jid: str
    started_at: str
    last_activity_at: str
    current_level: str | None = None
    applied_changes: int = 0
    is_waiting: bool = False
    next: list[str] | None = None


class CancelResponse(BaseModel):
    thread_id: str
    status: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@api_router.post("/api/reprioritize", response_model=StartResponse)
async def start_reprioritize(body: StartRequest):
    """Start a new reverse cascade session."""
    thread_id = str(uuid4())

    try:
        await create_session(thread_id, body.chat_jid)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    log.info(
        "starting_reverse_cascade",
        thread_id=thread_id,
        chat_jid=body.chat_jid,
        user_request=body.user_request,
    )

    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = await _graph.ainvoke(
            {
                "user_request": body.user_request,
                "data_dir": body.data_dir,
                "chat_jid": body.chat_jid,
                "api_key": body.api_key,
                "propagation_stopped": False,
                "applied_changes": [],
                "current_analysis": None,
                "last_approval_response": None,
                "checkpoint_message": "",
                "cascade_files": {},
            },
            config,
        )
    except Exception:
        log.exception("failed_to_start_reverse_cascade")
        await delete_session(thread_id)
        raise HTTPException(status_code=500, detail="Failed to start reverse cascade")

    state = await _graph.aget_state(config)

    return StartResponse(
        thread_id=thread_id,
        status="awaiting_approval",
        checkpoint=CheckpointInfo(
            level=result.get("current_level", ""),
            message=result.get("checkpoint_message", ""),
        ),
        next=list(state.next) if state.next else None,
    )


@api_router.post("/api/reprioritize/{thread_id}/respond", response_model=RespondResponse)
async def respond_to_checkpoint(thread_id: str, body: RespondRequest):
    """Send approval/rejection for current checkpoint."""
    session = await get_session(thread_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    await touch_session(thread_id)

    log.info("resuming_with_response", thread_id=thread_id, decision=body.decision)

    config = {"configurable": {"thread_id": thread_id}}

    try:
        response_data = {"decision": body.decision, "feedback": body.feedback}
        result = await _graph.ainvoke(
            Command(resume=response_data),
            config,
        )
    except Exception:
        log.exception("failed_to_process_response")
        raise HTTPException(status_code=500, detail="Failed to process response")

    state = await _graph.aget_state(config)
    is_complete = not state.next or len(state.next) == 0

    if is_complete:
        await delete_session(thread_id)
        applied = result.get("applied_changes", [])
        return RespondResponse(
            thread_id=thread_id,
            status="completed",
            applied_changes=[
                {"level": c.level, "summary": c.summary}
                for c in applied
            ] if applied else None,
        )

    return RespondResponse(
        thread_id=thread_id,
        status="awaiting_approval",
        checkpoint=CheckpointInfo(
            level=result.get("current_level", ""),
            message=result.get("checkpoint_message", ""),
        ),
        next=list(state.next) if state.next else None,
    )


@api_router.get("/api/reprioritize/{thread_id}/status", response_model=StatusResponse)
async def get_reprioritize_status(thread_id: str):
    """Check session progress."""
    session = await get_session(thread_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    config = {"configurable": {"thread_id": thread_id}}
    state = await _graph.aget_state(config)

    values = state.values or {}

    return StatusResponse(
        thread_id=thread_id,
        chat_jid=session["chat_jid"],
        started_at=session["started_at"],
        last_activity_at=session["last_activity_at"],
        current_level=values.get("current_level"),
        applied_changes=len(values.get("applied_changes", [])),
        is_waiting=bool(state.next and len(state.next) > 0),
        next=list(state.next) if state.next else None,
    )


@api_router.delete("/api/reprioritize/{thread_id}", response_model=CancelResponse)
async def cancel_reprioritize(thread_id: str):
    """Cancel session and rollback all changes."""
    session = await get_session(thread_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found or expired")

    # Get data_dir from graph state for cleanup
    config = {"configurable": {"thread_id": thread_id}}
    state = await _graph.aget_state(config)
    data_dir = (state.values or {}).get("data_dir", "")

    if data_dir:
        cleanup_backups(thread_id, data_dir)

    await delete_session(thread_id)

    log.info("session_cancelled", thread_id=thread_id)
    return CancelResponse(thread_id=thread_id, status="cancelled")
