import uuid
from datetime import datetime

from pydantic import BaseModel


class TaskIODefinitionResponse(BaseModel):
    id: uuid.UUID
    task_definition_id: uuid.UUID
    io_type: str
    data_key: str
    data_type: str
    description: str | None
    required: bool
    source_task_definition_id: uuid.UUID | None
    created_at: datetime

    model_config = {"from_attributes": True}


class TaskIOInstanceResponse(BaseModel):
    id: uuid.UUID
    task_io_definition_id: uuid.UUID
    task_instance_id: uuid.UUID
    project_id: uuid.UUID
    data: dict | None
    status: str
    produced_at: datetime | None
    consumed_by: list | None

    model_config = {"from_attributes": True}


class TaskIOInstanceCreate(BaseModel):
    task_io_definition_id: uuid.UUID
    task_instance_id: uuid.UUID
    project_id: uuid.UUID
    data: dict | None = None


class TaskIOInstanceUpdate(BaseModel):
    data: dict | None = None
    status: str | None = None


class TaskIODefinitionCreate(BaseModel):
    task_definition_id: uuid.UUID
    io_type: str  # INPUT / OUTPUT
    data_key: str
    data_type: str
    description: str | None = None
    required: bool = True
    source_task_definition_id: uuid.UUID | None = None
