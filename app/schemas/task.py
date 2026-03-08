import uuid
from datetime import datetime

from pydantic import BaseModel


class TaskDefinitionResponse(BaseModel):
    id: uuid.UUID
    phase_definition_id: uuid.UUID
    name: str
    description: str | None
    classification: str
    hybrid_pattern: str | None
    default_owner_role: str
    secondary_owner_role: str | None
    source_type: str | None
    sort_order: int
    maps_to_document: str | None
    maps_to_gate_item: str | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskInstanceResponse(BaseModel):
    id: uuid.UUID
    task_definition_id: uuid.UUID
    phase_instance_id: uuid.UUID
    project_id: uuid.UUID
    assigned_to: uuid.UUID | None
    assigned_by: str
    status: str
    trust_level: str
    classification: str
    priority: str
    due_date: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    ai_confidence: float | None
    escalated: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskInstanceDetail(TaskInstanceResponse):
    """Task instance with definition info."""
    task_name: str | None = None
    task_description: str | None = None


class TaskInstanceUpdate(BaseModel):
    status: str | None = None
    assigned_to: uuid.UUID | None = None
    priority: str | None = None
    trust_level: str | None = None
    classification: str | None = None
    due_date: datetime | None = None


class TaskCompleteRequest(BaseModel):
    ai_output: dict | None = None
    human_feedback: dict | None = None
