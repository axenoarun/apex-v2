import uuid
from datetime import datetime

from pydantic import BaseModel


class KnowledgeCreate(BaseModel):
    knowledge_type: str
    source_project_id: uuid.UUID
    content: dict | None = None
    confidence: float


class KnowledgeResponse(BaseModel):
    id: uuid.UUID
    knowledge_type: str
    source_project_id: uuid.UUID
    content: dict | None
    confidence: float
    times_used: int
    times_successful: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeUpdate(BaseModel):
    content: dict | None = None
    confidence: float | None = None
