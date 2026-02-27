"""Node: analyze the impact of a change at the current cascade level."""

from __future__ import annotations

import json
import re

import structlog

from cascade_api.cascade.level_utils import CascadeLevel
from cascade_api.graph.state import Analysis, ReverseCascadeState
from cascade_api.llm.client import ask
from cascade_api.llm.prompts import ANALYZE_IMPACT_SYSTEM, build_analyze_impact_prompt

log = structlog.get_logger()


async def analyze_impact(state: ReverseCascadeState) -> dict:
    """Build prompt, ask Claude, parse JSON, format checkpoint message."""
    level: CascadeLevel = state["current_level"]
    cascade_files = state.get("cascade_files", {})
    file_info = cascade_files.get(level)

    if not file_info:
        log.warning("no_file_for_level", level=level)
        return {
            "current_analysis": Analysis(
                level=level,
                impact_summary=f"No file found for {level} level",
                proposed_content="",
                requires_propagation=False,
            ),
        }

    log.info("analyzing_impact", level=level, file=file_info["path"])

    applied = state.get("applied_changes", [])
    changes_context = [
        {"level": c.level, "summary": c.summary, "content": c.new_content}
        for c in applied
    ]

    prompt = build_analyze_impact_prompt(
        state["user_request"],
        level,
        file_info["content"],
        changes_context,
    )

    raw = await ask(ANALYZE_IMPACT_SYSTEM, prompt, state["api_key"])

    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        raise ValueError(f"Failed to parse impact analysis response: {raw}")

    parsed = json.loads(json_match.group(0))

    analysis = Analysis(
        level=level,
        impact_summary=parsed["impactSummary"],
        proposed_content=parsed["proposedContent"],
        requires_propagation=parsed["requiresPropagation"],
    )

    log.info(
        "impact_analysis_complete",
        level=level,
        requires_propagation=analysis.requires_propagation,
        summary=analysis.impact_summary,
    )

    checkpoint_message = _format_checkpoint_message(level, analysis)

    return {
        "current_analysis": analysis,
        "checkpoint_message": checkpoint_message,
    }


def _format_checkpoint_message(level: CascadeLevel, analysis: Analysis) -> str:
    """Build a human-readable checkpoint message for WhatsApp/API."""
    proposed_preview = analysis.proposed_content[:1500]
    if len(analysis.proposed_content) > 1500:
        proposed_preview += "\n..."

    return "\n".join([
        f"*Reverse Cascade — {level.upper()} level*",
        "",
        f"*Impact:* {analysis.impact_summary}",
        "",
        "*Proposed changes:*",
        "```",
        proposed_preview,
        "```",
        "",
        "Reply with:",
        "- *approve* — accept and continue cascading up",
        "- *reject* — discard changes, stop",
        "- *stop* — accept changes but don't cascade further",
        "- *modify: [your feedback]* — revise the proposal",
    ])
