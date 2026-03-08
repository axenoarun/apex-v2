"""
Agent service — handles agent execution lifecycle and orchestration.
"""
import uuid
import time
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentDefinition, AgentExecution
from app.models.cost import CostTracking
from app.services.audit import log_audit


async def get_agent_definition(db: AsyncSession, name: str) -> AgentDefinition | None:
    result = await db.execute(
        select(AgentDefinition).where(AgentDefinition.name == name)
    )
    return result.scalar_one_or_none()


async def list_agent_definitions(db: AsyncSession) -> list[AgentDefinition]:
    result = await db.execute(
        select(AgentDefinition)
        .where(AgentDefinition.is_active == True)  # noqa: E712
        .order_by(AgentDefinition.name)
    )
    return list(result.scalars().all())


async def create_execution(
    db: AsyncSession,
    *,
    agent_definition_id: uuid.UUID,
    project_id: uuid.UUID,
    task_instance_id: uuid.UUID | None = None,
    triggered_by: str,
    input_context: dict | None = None,
) -> AgentExecution:
    """Create a new agent execution record (status=PENDING)."""
    execution = AgentExecution(
        agent_definition_id=agent_definition_id,
        project_id=project_id,
        task_instance_id=task_instance_id,
        triggered_by=triggered_by,
        input_context=input_context,
        status="PENDING",
        tokens_input=0,
        tokens_output=0,
        cost_usd=Decimal("0"),
    )
    db.add(execution)
    await db.flush()

    await log_audit(
        db,
        actor_type="SYSTEM",
        actor_id=None,
        action="CREATE_EXECUTION",
        entity_type="agent_execution",
        entity_id=execution.id,
        project_id=project_id,
        new_value={"agent_definition_id": str(agent_definition_id), "triggered_by": triggered_by},
    )

    await db.refresh(execution)
    return execution


async def complete_execution(
    db: AsyncSession,
    execution_id: uuid.UUID,
    *,
    output: dict,
    tokens_input: int,
    tokens_output: int,
    cost_usd: Decimal,
    confidence_score: float | None = None,
    tools_called: list | None = None,
    duration_ms: int | None = None,
) -> AgentExecution:
    """Mark an execution as completed with results."""
    result = await db.execute(
        select(AgentExecution).where(AgentExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise ValueError("Agent execution not found")

    execution.output = output
    execution.tokens_input = tokens_input
    execution.tokens_output = tokens_output
    execution.cost_usd = cost_usd
    execution.confidence_score = confidence_score
    execution.tools_called = tools_called
    execution.duration_ms = duration_ms
    execution.status = "COMPLETED"
    execution.completed_at = datetime.now(timezone.utc)

    # Track cost
    cost_entry = CostTracking(
        project_id=execution.project_id,
        phase_instance_id=None,
        task_instance_id=execution.task_instance_id,
        agent_execution_id=execution.id,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        cost_usd=cost_usd,
    )
    db.add(cost_entry)
    await db.flush()
    await db.refresh(execution)
    return execution


async def pause_execution(
    db: AsyncSession,
    execution_id: uuid.UUID,
    reason: dict,
) -> AgentExecution:
    """Pause an agent execution (e.g., needs human input)."""
    result = await db.execute(
        select(AgentExecution).where(AgentExecution.id == execution_id)
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise ValueError("Agent execution not found")

    execution.paused = True
    execution.pause_reason = reason
    execution.status = "PAUSED"
    await db.flush()
    await db.refresh(execution)
    return execution


async def list_executions(
    db: AsyncSession,
    *,
    project_id: uuid.UUID | None = None,
    task_instance_id: uuid.UUID | None = None,
    agent_definition_id: uuid.UUID | None = None,
    status: str | None = None,
) -> list[AgentExecution]:
    query = select(AgentExecution)
    if project_id:
        query = query.where(AgentExecution.project_id == project_id)
    if task_instance_id:
        query = query.where(AgentExecution.task_instance_id == task_instance_id)
    if agent_definition_id:
        query = query.where(AgentExecution.agent_definition_id == agent_definition_id)
    if status:
        query = query.where(AgentExecution.status == status)
    query = query.order_by(AgentExecution.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_execution(db: AsyncSession, execution_id: uuid.UUID) -> AgentExecution | None:
    result = await db.execute(
        select(AgentExecution).where(AgentExecution.id == execution_id)
    )
    return result.scalar_one_or_none()
