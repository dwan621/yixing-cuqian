from __future__ import annotations
from pydantic import BaseModel, Field


class RequirementInput(BaseModel):
    industry: str = Field(..., min_length=1)
    scenario: str = Field(..., min_length=1)
    scale: str = Field(..., min_length=1)
    demo_minutes: int = Field(..., gt=0, le=120)
    background: str | None = None
    template: str | None = None


class GenerateResponse(BaseModel):
    session_id: str


class PlanResult(BaseModel):
    session_id: str
    markdown: str
    functions: list[dict]
    mock_data: dict
    architecture: str
    demo_script: dict
