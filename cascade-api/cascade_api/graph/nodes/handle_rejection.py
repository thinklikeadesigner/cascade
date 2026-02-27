"""Node: handle a rejected change — restore backups and stop propagation."""

from __future__ import annotations

import structlog

from cascade_api.cascade.file_writer import restore_backups
from cascade_api.graph.state import ReverseCascadeState

log = structlog.get_logger()


async def handle_rejection(state: ReverseCascadeState) -> dict:
    """Restore backups and mark propagation as stopped."""
    thread_id = state["chat_jid"]
    data_dir = state["data_dir"]
    level = state["current_level"]

    log.info("change_rejected", level=level, thread_id=thread_id)

    restored = restore_backups(thread_id, data_dir)
    if restored:
        log.info("backups_restored", count=len(restored))

    return {
        "propagation_stopped": True,
        "checkpoint_message": f"Changes at {level} level rejected. All changes rolled back.",
    }
