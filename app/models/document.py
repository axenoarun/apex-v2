import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DocumentTemplate(Base):
    __tablename__ = "document_template"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    phase_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("phase_definition.id"), nullable=False)
    template_structure: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_format: Mapped[str] = mapped_column(String, nullable=False)  # DOCX / XLSX / PDF / MD
    ai_generation_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    phase_definition = relationship("PhaseDefinition")


class DocumentInstance(Base):
    __tablename__ = "document_instance"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("document_template.id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    phase_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("phase_instance.id"), nullable=False)
    task_instance_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("task_instance.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="NOT_STARTED")  # NOT_STARTED / AI_DRAFTING / DRAFT / IN_REVIEW / REVISION_REQUESTED / FINAL / EXPORTED
    generated_by: Mapped[str] = mapped_column(String, nullable=False)  # AI / HUMAN
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    document_template = relationship("DocumentTemplate")
    project = relationship("Project")
    phase_instance = relationship("PhaseInstance")
    task_instance = relationship("TaskInstance")
    reviewer = relationship("User", foreign_keys=[reviewed_by])
