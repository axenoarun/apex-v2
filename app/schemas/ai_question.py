import uuid
from datetime import datetime

from pydantic import BaseModel


class AIQuestionCreate(BaseModel):
    project_id: uuid.UUID
    phase_instance_id: uuid.UUID
    task_instance_id: uuid.UUID | None = None
    target_role: str
    question_text: str
    question_type: str
    question_context: dict | None = None
    maps_to_document_field: str | None = None
    maps_to_gate_item: str | None = None
    batch_id: uuid.UUID | None = None


class AIQuestionResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    phase_instance_id: uuid.UUID
    task_instance_id: uuid.UUID | None
    target_role: str
    question_text: str
    question_type: str
    question_context: dict | None
    maps_to_document_field: str | None
    maps_to_gate_item: str | None
    batch_id: uuid.UUID | None
    answer: str | None
    answered_by: uuid.UUID | None
    answered_at: datetime | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class AIQuestionAnswer(BaseModel):
    answer: str


class AIQuestionBatchCreate(BaseModel):
    """Create multiple questions in a batch."""
    project_id: uuid.UUID
    phase_instance_id: uuid.UUID
    task_instance_id: uuid.UUID | None = None
    target_role: str
    questions: list[dict]  # [{question_text, question_type, ...}]
