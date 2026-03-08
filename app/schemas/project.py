import uuid
from datetime import datetime

from pydantic import BaseModel


class ProjectCreate(BaseModel):
    organization_id: uuid.UUID
    name: str
    client_name: str
    description: str | None = None


class ProjectUpdate(BaseModel):
    name: str | None = None
    client_name: str | None = None
    description: str | None = None
    status: str | None = None


class ProjectResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    client_name: str
    description: str | None
    status: str
    current_phase_id: uuid.UUID | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectDetail(ProjectResponse):
    """Project with nested phase instances."""
    phase_instances: list["PhaseInstanceResponse"] = []


# Forward ref resolved after PhaseInstanceResponse is defined
from app.schemas.phase import PhaseInstanceResponse  # noqa: E402
ProjectDetail.model_rebuild()
