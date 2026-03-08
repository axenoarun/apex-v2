import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CostTracking(Base):
    __tablename__ = "cost_tracking"
    __table_args__ = (
        Index("ix_cost_tracking_project_phase", "project_id", "phase_instance_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    phase_instance_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("phase_instance.id"), nullable=True)
    task_instance_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("task_instance.id"), nullable=True)
    agent_execution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("agent_execution.id"), nullable=False)
    tokens_input: Mapped[int] = mapped_column(Integer, nullable=False)
    tokens_output: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd = mapped_column(Numeric(10, 6), nullable=False)
    is_rework: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rework_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    is_eval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    eval_definition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("eval_definition.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project = relationship("Project")
    phase_instance = relationship("PhaseInstance")
    task_instance = relationship("TaskInstance")
    agent_execution = relationship("AgentExecution")
    eval_definition = relationship("EvalDefinition")
