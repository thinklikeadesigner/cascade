"""Edge: route based on the user's approval decision."""

from __future__ import annotations

from cascade_api.graph.state import ReverseCascadeState


def route_approval(state: ReverseCascadeState) -> str:
    """Return the next node name based on the user's decision."""
    response = state.get("last_approval_response")
    if not response:
        raise ValueError("No approval response found")

    decision = response.decision
    if decision in ("approve", "stop"):
        return "apply_changes"
    elif decision == "reject":
        return "handle_rejection"
    elif decision == "modify":
        # Re-analyze with feedback incorporated
        return "analyze_impact"
    else:
        raise ValueError(f"Unknown decision: {decision}")
