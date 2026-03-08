import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Index, Integer, Numeric, String,
    Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AgentDefinition(Base):
    __tablename__ = "agent_definition"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    display_name: Mapped[str | None] = mapped_column(String, nullable=True)
    role_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    model: Mapped[str | None] = mapped_column(String, nullable=True)
    memory_scope: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tools: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    input_sources: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output_targets: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    max_tokens_per_call: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.3)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    executions = relationship("AgentExecution", back_populates="agent_definition")


class AgentExecution(Base):
    __tablename__ = "agent_execution"
    __table_args__ = (
        Index("ix_agent_execution_project_created", "project_id", "created_at", postgresql_using="btree"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_definition.id"), nullable=False)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    task_instance_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("task_instance.id"), nullable=True)
    triggered_by: Mapped[str] = mapped_column(String, nullable=False)
    input_context: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    output: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tools_called: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    eval_scores: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    paused: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    pause_reason: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd = mapped_column(Numeric(10, 6), nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent_definition = relationship("AgentDefinition", back_populates="executions")
    project = relationship("Project")
    task_instance = relationship("TaskInstance")
