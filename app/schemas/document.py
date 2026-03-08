import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentTemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    phase_definition_id: uuid.UUID
    template_structure: dict | None
    output_format: str
    ai_generation_prompt: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentInstanceCreate(BaseModel):
    document_template_id: uuid.UUID
    project_id: uuid.UUID
    phase_instance_id: uuid.UUID
    task_instance_id: uuid.UUID | None = None


class DocumentInstanceResponse(BaseModel):
    id: uuid.UUID
    document_template_id: uuid.UUID
    project_id: uuid.UUID
    phase_instance_id: uuid.UUID
    task_instance_id: uuid.UUID | None
    status: str
    generated_by: str
    content: dict | None
    version: int
    reviewed_by: uuid.UUID | None
    exported_at: datetime | None
    file_path: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentInstanceUpdate(BaseModel):
    status: str | None = None
    content: dict | None = None
    version: int | None = None


class DocumentReviewRequest(BaseModel):
    approved: bool
    comments: str | None = None
