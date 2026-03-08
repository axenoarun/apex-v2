import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: str
    name: str
    password: str
    organization_id: uuid.UUID


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    email: str
    name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserWithRoles(UserResponse):
    roles: list[dict] = []
