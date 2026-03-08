import uuid
from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID | None
    actor_type: str
    actor_id: uuid.UUID | None
    action: str
    entity_type: str
    entity_id: uuid.UUID
    old_value: dict | None
    new_value: dict | None
    extra_data: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
