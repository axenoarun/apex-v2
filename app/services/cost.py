"""Cost tracking service — records and aggregates AI execution costs.

Per spec Section 9.1: every Claude call (task execution + eval) creates a CostTracking record.
"""

import logging
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cost import CostTracking

logger = logging.getLogger(__name__)


async def record_cost(
    db: AsyncSession,
    *,
    project_id: uuid.UUID,
    agent_execution_id: uuid.UUID,
    tokens_input: int,
    tokens_output: int,
    cost_usd: Decimal,
    is_rework: bool = False,
    rework_reason: str | None = None,
    is_eval: bool = False,
    eval_definition_id: uuid.UUID | None = None,
    phase_instance_id: uuid.UUID | None = None,
    task_instance_id: uuid.UUID | None = None,
) -> CostTracking:
    """Create a CostTracking record for a Claude API call."""
    record = CostTracking(
        project_id=project_id,
        phase_instance_id=phase_instance_id,
        task_instance_id=task_instance_id,
        agent_execution_id=agent_execution_id,
        tokens_input=tokens_input,
        tokens_output=tokens_output,
        cost_usd=cost_usd,
        is_rework=is_rework,
        rework_reason=rework_reason,
        is_eval=is_eval,
        eval_definition_id=eval_definition_id,
    )
    db.add(record)
    await db.flush()
    return record


async def get_project_costs(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> dict:
    """Aggregate cost metrics for a project."""
    # Total costs
    total_q = await db.execute(
        select(
            func.coalesce(func.sum(CostTracking.cost_usd), 0).label("total_cost"),
            func.coalesce(func.sum(CostTracking.tokens_input), 0).label("total_input"),
            func.coalesce(func.sum(CostTracking.tokens_output), 0).label("total_output"),
            func.count(CostTracking.id).label("total_calls"),
        ).where(CostTracking.project_id == project_id)
    )
    total = total_q.one()

    # Rework costs
    rework_q = await db.execute(
        select(
            func.coalesce(func.sum(CostTracking.cost_usd), 0).label("rework_cost"),
            func.count(CostTracking.id).label("rework_calls"),
        ).where(
            CostTracking.project_id == project_id,
            CostTracking.is_rework.is_(True),
        )
    )
    rework = rework_q.one()

    # Eval costs
    eval_q = await db.execute(
        select(
            func.coalesce(func.sum(CostTracking.cost_usd), 0).label("eval_cost"),
            func.count(CostTracking.id).label("eval_calls"),
        ).where(
            CostTracking.project_id == project_id,
            CostTracking.is_eval.is_(True),
        )
    )
    eval_row = eval_q.one()

    total_cost = float(total.total_cost)
    rework_cost = float(rework.rework_cost)

    return {
        "total_cost_usd": total_cost,
        "total_tokens_input": total.total_input,
        "total_tokens_output": total.total_output,
        "total_calls": total.total_calls,
        "rework_cost_usd": rework_cost,
        "rework_calls": rework.rework_calls,
        "rework_percentage": (rework_cost / total_cost * 100) if total_cost > 0 else 0.0,
        "eval_cost_usd": float(eval_row.eval_cost),
        "eval_calls": eval_row.eval_calls,
    }


async def get_project_costs_by_phase(
    db: AsyncSession,
    project_id: uuid.UUID,
) -> list[dict]:
    """Get cost breakdown by phase for a project."""
    result = await db.execute(
        select(
            CostTracking.phase_instance_id,
            func.coalesce(func.sum(CostTracking.cost_usd), 0).label("phase_cost"),
            func.coalesce(func.sum(CostTracking.tokens_input), 0).label("tokens_input"),
            func.coalesce(func.sum(CostTracking.tokens_output), 0).label("tokens_output"),
            func.count(CostTracking.id).label("call_count"),
        )
        .where(CostTracking.project_id == project_id)
        .group_by(CostTracking.phase_instance_id)
    )
    return [
        {
            "phase_instance_id": str(row.phase_instance_id) if row.phase_instance_id else None,
            "cost_usd": float(row.phase_cost),
            "tokens_input": row.tokens_input,
            "tokens_output": row.tokens_output,
            "call_count": row.call_count,
        }
        for row in result.all()
    ]
