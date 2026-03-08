import uuid
from datetime import datetime

from pydantic import BaseModel


class ImprovementProposalCreate(BaseModel):
    project_id: uuid.UUID | None = None
    generated_by_agent_execution_id: uuid.UUID
    proposal_type: str
    title: str
    description: str
    evidence: dict | None = None


class ImprovementProposalResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID | None
    generated_by_agent_execution_id: uuid.UUID
    proposal_type: str
    title: str
    description: str
    evidence: dict | None
    status: str
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ImprovementReviewRequest(BaseModel):
    status: str  # ACCEPTED / REJECTED / DEFERRED
