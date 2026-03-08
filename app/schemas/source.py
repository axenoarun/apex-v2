import uuid
from datetime import datetime

from pydantic import BaseModel


class SourceDefinitionResponse(BaseModel):
    id: uuid.UUID
    name: str
    source_type: str
    is_mandatory: bool
    business_type: str
    description: str | None
    implementation_owner_role: str | None
    requires_client_admin: bool
    client_dependencies: list | None
    ai_scope: str | None
    artifacts: list | None
    layers: list | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SourceInstanceResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    source_definition_id: uuid.UUID
    status: str
    current_layer: str | None
    pilot_status: str | None
    dev_status: str | None
    prod_status: str | None
    client_credentials_provided: bool
    client_etl_complete: bool
    schema_id: str | None
    dataset_id: str | None
    connection_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SourceInstanceDetail(SourceInstanceResponse):
    """Source instance with definition info."""
    source_name: str | None = None
    source_type: str | None = None


class SourceInstanceUpdate(BaseModel):
    status: str | None = None
    current_layer: str | None = None
    pilot_status: str | None = None
    dev_status: str | None = None
    prod_status: str | None = None
    client_credentials_provided: bool | None = None
    client_etl_complete: bool | None = None
    schema_id: str | None = None
    dataset_id: str | None = None
    connection_id: str | None = None


class SourceSelectRequest(BaseModel):
    """Select which sources apply to a project."""
    source_definition_ids: list[uuid.UUID]
