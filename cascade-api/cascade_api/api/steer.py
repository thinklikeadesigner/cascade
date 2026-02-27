"""POST /api/steer — evaluate a task's ROI against the user's goal."""

from __future__ import annotations

from pydantic import BaseModel

from cascade_api.api.router import api_router
from cascade_api.dependencies import get_supabase
from cascade_api.steer.evaluate import evaluate_task_roi


class SteerRequest(BaseModel):
    tenant_id: str
    goal_id: str
    task_description: str
    api_key: str


class MatchedSkill(BaseModel):
    skill_name: str
    weight: float
    proficiency: float
    contribution: float


class SteerResponse(BaseModel):
    alignment_score: float
    matched_skills: list[MatchedSkill]
    suggestion: str | None
    alternatives: list[str]


@api_router.post("/api/steer", response_model=SteerResponse)
async def steer_endpoint(body: SteerRequest) -> SteerResponse:
    """Evaluate a proposed task's alignment with the user's goal."""
    supabase = get_supabase()
    result = await evaluate_task_roi(
        supabase=supabase,
        tenant_id=body.tenant_id,
        goal_id=body.goal_id,
        task_description=body.task_description,
        api_key=body.api_key,
    )
    return SteerResponse(**result)
