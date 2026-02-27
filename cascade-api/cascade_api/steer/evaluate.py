"""ROI evaluation for tasks — suggest, don't reject."""

from __future__ import annotations

import json

import structlog
from supabase import Client as SupabaseClient

from cascade_api.dependencies import get_anthropic

log = structlog.get_logger()

TASK_SKILL_MAPPING_PROMPT = """\
Given the following task description, identify which skills it exercises.

Return ONLY a JSON array of skill name strings — no markdown, no explanation.
Use lowercase, concise names (1-3 words).

Example: ["algorithms", "system design", "python"]

Task: {task_description}
"""

ALTERNATIVE_SUGGESTION_PROMPT = """\
A user is working toward a goal. Their proposed task has low alignment ({score:.0%}) \
with the goal's skill requirements.

Goal skills and current gaps (sorted by largest gap):
{gaps_text}

Proposed task: {task_description}
Matched skills: {matched_skills}

Suggest 2-3 higher-leverage alternative tasks that would close the biggest skill gaps. \
Be concrete and actionable. Return ONLY a JSON array of strings — no markdown.

Example: ["Solve 5 LeetCode medium graph problems", "Design a URL shortener system"]
"""


async def evaluate_task_roi(
    supabase: SupabaseClient,
    tenant_id: str,
    goal_id: str,
    task_description: str,
    api_key: str,
) -> dict:
    """Evaluate a task's ROI against the user's goal and skill profile.

    Returns:
        {
            alignment_score: float (0.0-1.0),
            matched_skills: [{skill_name, weight, proficiency, contribution}],
            suggestion: str | None,
            alternatives: [str]
        }
    """
    client = get_anthropic(api_key)

    # Step 1: Map task to skills via Claude
    message = await client.messages.create(
        model="claude-sonnet-4-5-20250514",
        max_tokens=256,
        messages=[
            {
                "role": "user",
                "content": TASK_SKILL_MAPPING_PROMPT.format(
                    task_description=task_description
                ),
            }
        ],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1]
        if raw.endswith("```"):
            raw = raw[: raw.rfind("```")]
    task_skills: list[str] = json.loads(raw)

    # Step 2: Get expert_skills for this goal
    expert_result = (
        supabase.table("expert_skills")
        .select("skill_name, weight")
        .eq("goal_id", goal_id)
        .execute()
    )
    expert_map: dict[str, float] = {
        row["skill_name"]: float(row["weight"]) for row in expert_result.data
    }

    # Step 3: Get user_skills
    user_result = (
        supabase.table("user_skills")
        .select("skill_name, proficiency")
        .eq("tenant_id", tenant_id)
        .execute()
    )
    user_map: dict[str, float] = {
        row["skill_name"]: float(row["proficiency"]) for row in user_result.data
    }

    # Step 4: Calculate alignment score
    matched_skills: list[dict] = []
    total_weight = 0.0
    weighted_gap_sum = 0.0

    for skill_name in task_skills:
        weight = expert_map.get(skill_name, 0.0)
        proficiency = user_map.get(skill_name, 0.0)
        contribution = weight * (1.0 - proficiency)
        matched_skills.append(
            {
                "skill_name": skill_name,
                "weight": weight,
                "proficiency": proficiency,
                "contribution": round(contribution, 4),
            }
        )
        total_weight += weight
        weighted_gap_sum += contribution

    # Normalize: alignment = weighted gap coverage relative to max possible
    max_possible = sum(float(r["weight"]) for r in expert_result.data) if expert_result.data else 1.0
    alignment_score = round(weighted_gap_sum / max_possible, 4) if max_possible > 0 else 0.0
    alignment_score = min(1.0, alignment_score)

    log.info(
        "steer.evaluated",
        task=task_description[:50],
        alignment=alignment_score,
        matched=len(matched_skills),
    )

    # Step 5: Suggest alternatives if low alignment
    suggestion: str | None = None
    alternatives: list[str] = []

    if alignment_score < 0.3:
        # Get skill gaps for context
        from cascade_api.steer.skill_tracker import get_skill_gaps

        gaps = await get_skill_gaps(supabase, tenant_id, goal_id)
        gaps_text = "\n".join(
            f"- {g['skill_name']}: weight={g['required_weight']}, "
            f"current={g['current_proficiency']}, gap={g['gap']}"
            for g in gaps[:8]
        )

        alt_message = await client.messages.create(
            model="claude-sonnet-4-5-20250514",
            max_tokens=512,
            messages=[
                {
                    "role": "user",
                    "content": ALTERNATIVE_SUGGESTION_PROMPT.format(
                        score=alignment_score,
                        gaps_text=gaps_text,
                        task_description=task_description,
                        matched_skills=[s["skill_name"] for s in matched_skills],
                    ),
                }
            ],
        )

        alt_raw = alt_message.content[0].text.strip()
        if alt_raw.startswith("```"):
            alt_raw = alt_raw.split("\n", 1)[1]
            if alt_raw.endswith("```"):
                alt_raw = alt_raw[: alt_raw.rfind("```")]
        alternatives = json.loads(alt_raw)

        suggestion = (
            f"This task has {alignment_score:.0%} alignment with your goal. "
            f"Higher-leverage alternatives: {', '.join(alternatives)}. "
            f"Still want to do it?"
        )

    return {
        "alignment_score": alignment_score,
        "matched_skills": matched_skills,
        "suggestion": suggestion,
        "alternatives": alternatives,
    }
