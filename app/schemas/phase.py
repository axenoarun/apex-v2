import uuid
from datetime import datetime

from pydantic import BaseModel


class PhaseDefinitionResponse(BaseModel):
    id: uuid.UUID
    name: str
    phase_number: int
    description: str | None
    gate_criteria: dict | None
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class PhaseInstanceResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    phase_definition_id: uuid.UUID
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    gate_results: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PhaseInstanceDetail(PhaseInstanceResponse):
    """Phase instance with definition info and task instances."""
    phase_name: str | None = None
    phase_number: int | None = None
    task_instances: list["TaskInstanceResponse"] = []


class PhaseGateOverride(BaseModel):
    reason: str


class PhaseAdvanceResponse(BaseModel):
    current_phase: PhaseInstanceResponse
    next_phase: PhaseInstanceResponse | None = None
    message: str


from app.schemas.task import TaskInstanceResponse  # noqa: E402
PhaseInstanceDetail.model_rebuild()
