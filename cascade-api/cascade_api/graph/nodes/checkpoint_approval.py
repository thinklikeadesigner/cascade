"""Node: pause the graph and wait for user approval via interrupt."""

from __future__ import annotations

import structlog
from langgraph.types import interrupt

from cascade_api.graph.state import ApprovalResponse, ReverseCascadeState

log = structlog.get_logger()


async def checkpoint_approval(state: ReverseCascadeState) -> dict:
    """Interrupt execution and wait for the user to approve/reject/modify.

    When the graph is resumed with ``Command(resume=response)``, the
    ``interrupt()`` call returns the response value.
    """
    level = state["current_level"]
    log.info("waiting_for_approval", level=level)

    # interrupt() pauses execution here.  The dict is metadata for the API layer.
    # When resumed, ``response`` contains the user's decision.
    response = interrupt({
        "level": level,
        "message": state.get("checkpoint_message", ""),
    })

    # response comes back as a dict from Command(resume=...)
    if isinstance(response, dict):
        approval = ApprovalResponse(**response)
    else:
        approval = response

    log.info("user_responded", level=level, decision=approval.decision)

    return {
        "last_approval_response": approval,
    }
