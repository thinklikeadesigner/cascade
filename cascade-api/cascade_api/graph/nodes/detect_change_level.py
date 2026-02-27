"""Node: detect which cascade level a user's change originates at."""

from __future__ import annotations

import json
import re

import structlog

from cascade_api.cascade.file_reader import read_cascade_files
from cascade_api.graph.state import ReverseCascadeState
from cascade_api.llm.client import ask
from cascade_api.llm.prompts import DETECT_LEVEL_SYSTEM, build_detect_level_prompt

log = structlog.get_logger()


async def detect_change_level(state: ReverseCascadeState) -> dict:
    """Read cascade files, ask Claude for the originating level, return state update."""
    user_request = state["user_request"]
    data_dir = state["data_dir"]
    api_key = state["api_key"]

    log.info("detecting_change_level", user_request=user_request, data_dir=data_dir)

    cascade_files = read_cascade_files(data_dir)

    prompt = build_detect_level_prompt(user_request, cascade_files)
    raw = await ask(DETECT_LEVEL_SYSTEM, prompt, api_key)

    # Parse JSON response from Claude
    json_match = re.search(r"\{[\s\S]*\}", raw)
    if not json_match:
        raise ValueError(f"Failed to parse level detection response: {raw}")

    parsed = json.loads(json_match.group(0))
    level = parsed["level"]
    reasoning = parsed.get("reasoning", "")

    log.info("change_level_detected", level=level, reasoning=reasoning)

    return {
        "origin_level": level,
        "current_level": level,
        "cascade_files": cascade_files,
    }
