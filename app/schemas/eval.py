import uuid
from datetime import datetime

from pydantic import BaseModel


class EvalDefinitionResponse(BaseModel):
    id: uuid.UUID
    name: str
    eval_type: str
    description: str | None
    eval_prompt: str | None
    threshold: float
    applies_to: dict | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalResultResponse(BaseModel):
    id: uuid.UUID
    eval_definition_id: uuid.UUID
    agent_execution_id: uuid.UUID
    task_instance_id: uuid.UUID | None
    project_id: uuid.UUID
    score: float
    passed: bool
    details: dict | None
    eval_tokens_used: int
    eval_cost_usd: float
    created_at: datetime

    model_config = {"from_attributes": True}


class EvalRunRequest(BaseModel):
    """Request to run evals against an agent execution."""
    agent_execution_id: uuid.UUID
    eval_definition_ids: list[uuid.UUID] | None = None  # None = run all applicable
