"""Edge + node: decide whether to propagate upward, and advance the level."""

from __future__ import annotations

from cascade_api.cascade.level_utils import get_next_level_up
from cascade_api.graph.state import ReverseCascadeState


def should_propagate(state: ReverseCascadeState) -> str:
    """After applying changes, decide whether to propagate upward or stop."""
    # User chose "stop" — accept changes but don't propagate
    last_response = state.get("last_approval_response")
    if (last_response and last_response.decision == "stop") or state.get("propagation_stopped"):
        return "__end__"

    # Check if analysis says propagation is needed
    analysis = state.get("current_analysis")
    if not analysis or not analysis.requires_propagation:
        return "__end__"

    # Check if there's a level above to propagate to
    next_level = get_next_level_up(state["current_level"])
    if not next_level:
        return "__end__"  # Already at year level

    # Check if we have a file for the next level
    cascade_files = state.get("cascade_files", {})
    if next_level not in cascade_files:
        return "__end__"  # No file at next level

    return "analyze_impact"


async def advance_level(state: ReverseCascadeState) -> dict:
    """Transition state to the next level up before re-entering analyze_impact."""
    next_level = get_next_level_up(state["current_level"])
    if not next_level:
        return {"propagation_stopped": True}

    return {
        "current_level": next_level,
        "current_analysis": None,
        "last_approval_response": None,
    }
