import uuid
from datetime import datetime

from pydantic import BaseModel


class FeedbackCreate(BaseModel):
    project_id: uuid.UUID
    agent_execution_id: uuid.UUID
    task_instance_id: uuid.UUID | None = None
    category: str
    severity: str
    description: str
    original_output: dict | None = None
    corrected_output: dict | None = None
    quality_score: float


class FeedbackResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    agent_execution_id: uuid.UUID
    task_instance_id: uuid.UUID | None
    submitted_by: uuid.UUID
    category: str
    severity: str
    description: str
    original_output: dict | None
    corrected_output: dict | None
    quality_score: float
    created_at: datetime

    model_config = {"from_attributes": True}
