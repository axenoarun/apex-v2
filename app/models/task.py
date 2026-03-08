import uuid
from datetime import datetime

from sqlalchemy import String, Text, Integer, Boolean, Float, ForeignKey, DateTime, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TaskDefinition(Base):
    __tablename__ = "task_definition"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phase_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("phase_definition.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification: Mapped[str] = mapped_column(String, nullable=False)  # AI / HYBRID / MANUAL
    hybrid_pattern: Mapped[str | None] = mapped_column(String, nullable=True)  # AI_DRAFTS_HUMAN_REVIEWS / HUMAN_INITIATES_AI_COMPLETES / AI_OPTIONS_HUMAN_PICKS
    default_owner_role: Mapped[str] = mapped_column(String, nullable=False)
    secondary_owner_role: Mapped[str | None] = mapped_column(String, nullable=True)
    source_type: Mapped[str | None] = mapped_column(String, nullable=True)  # WEB_MOBILE / SALESFORCE / RAINFOCUS / MARKETO / SIXSENSE / CJA_SETUP
    depends_on: Mapped[list | None] = mapped_column(JSONB, nullable=True)  # array of task_definition IDs
    default_trust_level: Mapped[str] = mapped_column(String, nullable=False, default="SUPERVISED")
    default_reminder_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=48)
    default_max_reminders: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    maps_to_document: Mapped[str | None] = mapped_column(String, nullable=True)
    maps_to_gate_item: Mapped[str | None] = mapped_column(String, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    phase_definition = relationship("PhaseDefinition", back_populates="task_definitions")


class TaskInstance(Base):
    __tablename__ = "task_instance"
    __table_args__ = (
        Index("ix_task_instance_project_status", "project_id", "status"),
        Index("ix_task_instance_assigned_status", "assigned_to", "status"),
        Index("ix_task_instance_phase_instance", "phase_instance_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("task_definition.id"), nullable=False)
    phase_instance_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("phase_instance.id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    assigned_by: Mapped[str] = mapped_column(String, nullable=False)  # AI / ARCHITECT
    status: Mapped[str] = mapped_column(String, nullable=False, default="NOT_STARTED")  # NOT_STARTED / WAITING_INPUT / AI_PROCESSING / AI_PAUSED_NEEDS_INPUT / IN_PROGRESS / IN_REVIEW / COMPLETED / BLOCKED / OVERDUE
    trust_level: Mapped[str] = mapped_column(String, nullable=False, default="SUPERVISED")
    classification: Mapped[str] = mapped_column(String, nullable=False)  # AI / HYBRID / MANUAL
    priority: Mapped[str] = mapped_column(String, nullable=False, default="MEDIUM")
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    reminder_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    escalated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    override_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=True)
    override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    human_feedback: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    parallel_prep_status: Mapped[str] = mapped_column(String, nullable=False, default="NONE")
    parallel_prep_output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    task_definition = relationship("TaskDefinition")
    phase_instance = relationship("PhaseInstance")
    project = relationship("Project")
    assignee = relationship("User", foreign_keys=[assigned_to])
    completer = relationship("User", foreign_keys=[completed_by])
    overrider = relationship("User", foreign_keys=[override_by])
