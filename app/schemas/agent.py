import uuid
from datetime import datetime

from pydantic import BaseModel


class AgentDefinitionResponse(BaseModel):
    id: uuid.UUID
    name: str
    display_name: str | None
    role_description: str | None
    model: str | None
    tools: list | None
    input_sources: dict | None
    output_targets: dict | None
    temperature: float
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentExecutionCreate(BaseModel):
    agent_definition_id: uuid.UUID
    project_id: uuid.UUID
    task_instance_id: uuid.UUID | None = None
    triggered_by: str
    input_context: dict | None = None


class AgentExecutionResponse(BaseModel):
    id: uuid.UUID
    agent_definition_id: uuid.UUID
    project_id: uuid.UUID
    task_instance_id: uuid.UUID | None
    triggered_by: str
    input_context: dict | None
    output: dict | None
    tools_called: list | None
    confidence_score: float | None
    eval_scores: dict | None
    paused: bool
    pause_reason: dict | None
    tokens_input: int
    tokens_output: int
    cost_usd: float
    duration_ms: int | None
    status: str
    created_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class AgentExecutionUpdate(BaseModel):
    output: dict | None = None
    confidence_score: float | None = None
    status: str | None = None
    paused: bool | None = None
    pause_reason: dict | None = None
