import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AIQuestion(Base):
    __tablename__ = "ai_question"
    __table_args__ = (
        Index("ix_ai_question_target_role_status", "target_role", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    phase_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("phase_instance.id"), nullable=False)
    task_instance_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("task_instance.id"), nullable=True)
    target_role: Mapped[str] = mapped_column(String, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String, nullable=False)
    question_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    maps_to_document_field: Mapped[str | None] = mapped_column(String, nullable=True)
    maps_to_gate_item: Mapped[str | None] = mapped_column(String, nullable=True)
    batch_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    answered_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project")
    phase_instance = relationship("PhaseInstance")
    task_instance = relationship("TaskInstance")
    answerer = relationship("User", foreign_keys=[answered_by])
