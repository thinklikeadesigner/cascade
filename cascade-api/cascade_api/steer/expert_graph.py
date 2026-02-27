"""Build an Expert Graph: decompose a goal into weighted skill requirements."""

from __future__ import annotations

import json

import structlog
from supabase import Client as SupabaseClient

from cascade_api.dependencies import get_anthropic

log = structlog.get_logger()

SKILL_DECOMPOSITION_PROMPT = """\
You are a goal-analysis engine. Given a goal, decompose it into the weighted \
skill requirements needed to achieve it.

Return ONLY a JSON array — no markdown fences, no explanation. Each element:
{{"skill_name": "...", "weight": 0.0-1.0, "category": "technical|business|creative|fitness|interpersonal|analytical"}}

Rules:
- weight represents how critical the skill is (1.0 = essential, 0.1 = minor)
- Include 5-15 skills
- category must be one of: technical, business, creative, fitness, interpersonal, analytical
- skill_name should be lowercase, concise (1-3 words)

Example for "Get a FAANG SWE offer":
[
  {{"skill_name": "algorithms", "weight": 0.95, "category": "technical"}},
  {{"skill_name": "system design", "weight": 0.85, "category": "technical"}},
  {{"skill_name": "behavioral interviews", "weight": 0.7, "category": "interpersonal"}},
  {{"skill_name": "coding speed", "weight": 0.6, "category": "technical"}},
  {{"skill_name": "networking", "weight": 0.3, "category": "interpersonal"}}
]

Goal: {goal_title}
Description: {goal_description}
"""


async def build_expert_graph(
    supabase: SupabaseClient,
    tenant_id: str,
    goal_id: str,
    api_key: str,
) -> list[dict]:
    """Decompose a goal into weighted skills and persist them.

    Uses Claude to analyse the goal, then writes rows to expert_skills.
    Any existing expert_skills for this goal_id are cleared first.
    """
    # Fetch the goal for context
    goal_result = (
        supabase.table("goals")
        .select("title, description")
        .eq("id", goal_id)
        .execute()
    )
    if not goal_result.data:
        raise ValueError(f"Goal {goal_id} not found")

    goal = goal_result.data[0]

    # Ask Claude to decompose
    client = get_anthropic(api_key)
    message = await client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": SKILL_DECOMPOSITION_PROMPT.format(
                    goal_title=goal["title"],
                    goal_description=goal.get("description") or "No description provided.",
                ),
            }
        ],
    )

    raw_text = message.content[0].text.strip()
    # Strip markdown fences if Claude adds them despite instructions
    if raw_text.startswith("```"):
        raw_text = raw_text.split("\n", 1)[1]
        if raw_text.endswith("```"):
            raw_text = raw_text[: raw_text.rfind("```")]

    skills: list[dict] = json.loads(raw_text)
    log.info(
        "expert_graph.decomposed",
        goal_id=goal_id,
        skill_count=len(skills),
    )

    # Clear existing expert_skills for this goal
    supabase.table("expert_skills").delete().eq("goal_id", goal_id).execute()

    # Insert new rows
    rows = [
        {
            "tenant_id": tenant_id,
            "goal_id": goal_id,
            "skill_name": s["skill_name"],
            "weight": s["weight"],
            "category": s.get("category"),
        }
        for s in skills
    ]
    result = supabase.table("expert_skills").insert(rows).execute()
    log.info("expert_graph.saved", goal_id=goal_id, rows=len(result.data))
    return result.data
