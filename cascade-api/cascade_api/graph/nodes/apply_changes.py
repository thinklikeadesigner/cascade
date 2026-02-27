"""Node: write approved changes to disk and record them in appliedChanges."""

from __future__ import annotations

import structlog

from cascade_api.cascade.file_writer import write_cascade_file
from cascade_api.graph.state import FileChange, ReverseCascadeState

log = structlog.get_logger()


async def apply_changes(state: ReverseCascadeState) -> dict:
    """Write the approved analysis to disk and append to applied_changes."""
    analysis = state.get("current_analysis")
    if not analysis or not analysis.proposed_content:
        log.warning("no_analysis_to_apply")
        return {}

    cascade_files = state.get("cascade_files", {})
    file_info = cascade_files.get(analysis.level)
    if not file_info:
        log.warning("no_file_to_write", level=analysis.level)
        return {}

    thread_id = state["chat_jid"]
    data_dir = state["data_dir"]

    write_cascade_file(file_info["path"], analysis.proposed_content, thread_id, data_dir)

    log.info("changes_applied", level=analysis.level, path=file_info["path"])

    change = FileChange(
        level=analysis.level,
        file_path=file_info["path"],
        original_content=file_info["content"],
        new_content=analysis.proposed_content,
        summary=analysis.impact_summary,
    )

    # Update cascade_files with new content so subsequent analysis uses it
    updated_files = {**cascade_files}
    updated_files[analysis.level] = {
        "path": file_info["path"],
        "content": analysis.proposed_content,
    }

    return {
        "applied_changes": [change],  # Reducer will append
        "cascade_files": updated_files,
    }
