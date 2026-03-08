import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey, DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SourceDefinition(Base):
    __tablename__ = "source_definition"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    source_type: Mapped[str] = mapped_column(String, nullable=False)  # WEB_MOBILE / SALESFORCE / RAINFOCUS / MARKETO / SIXSENSE
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False)
    business_type: Mapped[str] = mapped_column(String, nullable=False)  # ALL / B2B / B2C / B2B_B2C / BUSINESS_SPECIFIC
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    implementation_owner_role: Mapped[str | None] = mapped_column(String, nullable=True)
    requires_client_admin: Mapped[bool] = mapped_column(Boolean, nullable=False)
    client_dependencies: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ai_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    artifacts: Mapped[list] = mapped_column(JSONB, nullable=False, default=lambda: ["SCHEMA", "DATASET", "CONNECTION"])
    layers: Mapped[list] = mapped_column(JSONB, nullable=False, default=lambda: ["PILOT", "DEV", "PROD"])
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class SourceInstance(Base):
    __tablename__ = "source_instance"
    __table_args__ = (
        Index("ix_source_instance_project_status", "project_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    source_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source_definition.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="NOT_STARTED")  # NOT_STARTED / PILOT / DEV / PROD / COMPLETED
    current_layer: Mapped[str | None] = mapped_column(String, nullable=True)  # PILOT / DEV / PROD
    pilot_status: Mapped[str | None] = mapped_column(String, nullable=True)
    dev_status: Mapped[str | None] = mapped_column(String, nullable=True)
    prod_status: Mapped[str | None] = mapped_column(String, nullable=True)
    pilot_reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    prod_signed_off_by_architect: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    prod_signed_off_by_client: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    client_credentials_provided: Mapped[bool] = mapped_column(Boolean, default=False)
    client_etl_complete: Mapped[bool] = mapped_column(Boolean, default=False)
    schema_id: Mapped[str | None] = mapped_column(String, nullable=True)
    dataset_id: Mapped[str | None] = mapped_column(String, nullable=True)
    connection_id: Mapped[str | None] = mapped_column(String, nullable=True)
    error_log: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    project = relationship("Project")
    source_definition = relationship("SourceDefinition")
    pilot_reviewer = relationship("User", foreign_keys=[pilot_reviewed_by])
    architect_signoff = relationship("User", foreign_keys=[prod_signed_off_by_architect])
    client_signoff = relationship("User", foreign_keys=[prod_signed_off_by_client])
