"""Prompt templates for the reverse-cascade LLM calls."""

from __future__ import annotations

DETECT_LEVEL_SYSTEM = (
    "You are Cascade's change-level detector. Given a user's reprioritization "
    "request and their current cascade files, determine which level the change "
    "originates at.\n\n"
    "Cascade levels (lowest to highest): day, week, month, quarter, year\n\n"
    "Rules:\n"
    '- If the change is about today\'s tasks → "day"\n'
    '- If the change is about this week\'s plan → "week"\n'
    '- If the change affects monthly targets → "month"\n'
    '- If the change affects quarterly milestones → "quarter"\n'
    '- If the change affects yearly goals → "year"\n'
    "- When in doubt, pick the LOWEST level that fully captures the change. "
    "Changes propagate UP automatically.\n\n"
    'Respond with ONLY a JSON object: { "level": "week", "reasoning": "..." }'
)

ANALYZE_IMPACT_SYSTEM = (
    "You are Cascade's impact analyzer. Given a change at a lower level and a "
    "file at the current level, determine what changes are needed at this level "
    "to stay aligned.\n\n"
    "Cascade methodology:\n"
    "- **Gravity**: Plans cascade down (year → quarter → month → week → day). "
    "Reality flows up. When lower-level priorities change, higher levels must adapt.\n"
    "- **Core/Flex**: Core hours are the floor — the plan must succeed on Core "
    "alone. Flex is acceleration. Never overcommit Core.\n"
    "- **Checkpoints**: Every change requires human approval. Present changes "
    "clearly so the user can approve, modify, or reject.\n\n"
    "Rules:\n"
    "- Preserve the file's overall structure and formatting\n"
    "- Only change what's necessary to align with the lower-level changes\n"
    "- If no changes needed at this level, say so clearly\n"
    "- Always explain WHY each change is needed\n"
    "- Be specific about what's being added, removed, or modified\n\n"
    "Respond with a JSON object:\n"
    "{\n"
    '  "impactSummary": "Brief description of what changes and why",\n'
    '  "proposedContent": "The full updated file content",\n'
    '  "requiresPropagation": true/false,\n'
    '  "reasoning": "Why this level does/doesn\'t need further propagation upward"\n'
    "}"
)


def build_detect_level_prompt(
    user_request: str,
    files: dict[str, dict[str, str]],
) -> str:
    """Build the user message for the detect-level LLM call."""
    file_list = "\n\n".join(
        f"## {level}\n```\n{info['content']}\n```"
        for level, info in files.items()
    )
    return f'User\'s request: "{user_request}"\n\nCurrent cascade files:\n{file_list}'


def build_analyze_impact_prompt(
    user_request: str,
    current_level: str,
    current_content: str,
    applied_changes: list[dict[str, str]],
) -> str:
    """Build the user message for the analyze-impact LLM call."""
    if applied_changes:
        changes_below = "\n\n".join(
            f"### {c['level']} (approved)\nSummary: {c['summary']}\n```\n{c['content']}\n```"
            for c in applied_changes
        )
    else:
        changes_below = "No changes applied at lower levels yet."

    return (
        f'User\'s original request: "{user_request}"\n\n'
        f"Changes already applied at lower levels:\n{changes_below}\n\n"
        f"Current file at **{current_level}** level:\n```\n{current_content}\n```\n\n"
        f"Analyze what changes (if any) are needed at the {current_level} level "
        f"to stay aligned with the changes below."
    )
