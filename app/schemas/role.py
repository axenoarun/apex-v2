import uuid
from datetime import datetime
from pydantic import BaseModel


class RoleResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    permissions: dict | None
    is_system_role: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleAssign(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID


class RoleAssignResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    role_id: uuid.UUID
    assigned_at: datetime

    model_config = {"from_attributes": True}
