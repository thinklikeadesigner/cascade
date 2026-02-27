"""Reverse-cascade graph state definition."""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from pydantic import BaseModel

from cascade_api.cascade.level_utils import CascadeLevel


# ---------------------------------------------------------------------------
# Pydantic models for structured data inside the state
# ---------------------------------------------------------------------------

class FileChange(BaseModel):
    level: CascadeLevel
    file_path: str
    original_content: str
    new_content: str
    summary: str


class Analysis(BaseModel):
    level: CascadeLevel
    impact_summary: str
    proposed_content: str
    requires_propagation: bool


class ApprovalResponse(BaseModel):
    decision: str  # "approve" | "reject" | "stop" | "modify"
    feedback: str | None = None


# ---------------------------------------------------------------------------
# LangGraph state — TypedDict with Annotated reducer for appliedChanges
# ---------------------------------------------------------------------------

class ReverseCascadeState(TypedDict, total=False):
    # Input
    user_request: str
    data_dir: str
    chat_jid: str
    api_key: str

    # Level tracking
    origin_level: CascadeLevel
    current_level: CascadeLevel

    # File state — partial dict keyed by level
    cascade_files: dict[str, dict[str, str]]

    # Analysis at current level
    current_analysis: Analysis | None

    # Accumulated changes (reducer: append new changes)
    applied_changes: Annotated[list[FileChange], operator.add]

    # Approval flow
    last_approval_response: ApprovalResponse | None

    # Control flags
    propagation_stopped: bool

    # Message to send to user (for checkpoint)
    checkpoint_message: str

    # Multi-tenant / steer extensions
    tenant_id: str | None
    steer_evaluation: dict | None
