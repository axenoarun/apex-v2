import uuid
from datetime import datetime

from pydantic import BaseModel


class NotificationCreate(BaseModel):
    user_id: uuid.UUID
    project_id: uuid.UUID
    type: str
    title: str
    body: str
    action_url: str | None = None


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID
    type: str
    title: str
    body: str
    email_sent: bool
    read: bool
    read_at: datetime | None
    action_url: str | None
    created_at: datetime

    model_config = {"from_attributes": True}
