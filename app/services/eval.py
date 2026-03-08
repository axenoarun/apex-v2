"""
Eval service — runs automated evaluations against agent outputs.
"""
import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.eval import EvalDefinition, EvalResult
from app.models.agent import AgentExecution, AgentDefinition
from app.models.cost import CostTracking


async def list_eval_definitions(db: AsyncSession) -> list[EvalDefinition]:
    result = await db.execute(
        select(EvalDefinition)
        .where(EvalDefinition.is_active == True)  # noqa: E712
        .order_by(EvalDefinition.name)
    )
    return list(result.scalars().all())


async def get_applicable_evals(
    db: AsyncSession,
    agent_name: str,
) -> list[EvalDefinition]:
    """Get eval definitions that apply to a given agent."""
    all_evals = await list_eval_definitions(db)
    applicable = []
    for eval_def in all_evals:
        applies_to = eval_def.applies_to or {}
        agents = applies_to.get("agents", [])
        if agent_name in agents or not agents:
            applicable.append(eval_def)
    return applicable


async def record_eval_result(
    db: AsyncSession,
    *,
    eval_definition_id: uuid.UUID,
    agent_execution_id: uuid.UUID,
    task_instance_id: uuid.UUID | None,
    project_id: uuid.UUID,
    score: float,
    passed: bool,
    details: dict | None = None,
    eval_tokens_used: int = 0,
    eval_cost_usd: Decimal = Decimal("0"),
) -> EvalResult:
    eval_result = EvalResult(
        eval_definition_id=eval_definition_id,
        agent_execution_id=agent_execution_id,
        task_instance_id=task_instance_id,
        project_id=project_id,
        score=score,
        passed=passed,
        details=details,
        eval_tokens_used=eval_tokens_used,
        eval_cost_usd=eval_cost_usd,
    )
    db.add(eval_result)

    # Track eval cost separately
    if eval_tokens_used > 0:
        cost_entry = CostTracking(
            project_id=project_id,
            task_instance_id=task_instance_id,
            agent_execution_id=agent_execution_id,
            tokens_input=eval_tokens_used,
            tokens_output=0,
            cost_usd=eval_cost_usd,
            is_eval=True,
            eval_definition_id=eval_definition_id,
        )
        db.add(cost_entry)

    await db.flush()
    await db.refresh(eval_result)
    return eval_result


async def list_eval_results(
    db: AsyncSession,
    *,
    project_id: uuid.UUID | None = None,
    agent_execution_id: uuid.UUID | None = None,
) -> list[EvalResult]:
    query = select(EvalResult)
    if project_id:
        query = query.where(EvalResult.project_id == project_id)
    if agent_execution_id:
        query = query.where(EvalResult.agent_execution_id == agent_execution_id)
    query = query.order_by(EvalResult.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_project_eval_summary(db: AsyncSession, project_id: uuid.UUID) -> dict:
    """Get eval summary for a project."""
    results = await list_eval_results(db, project_id=project_id)
    if not results:
        return {"total_evals": 0, "passed": 0, "failed": 0, "avg_score": 0.0}

    passed = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / len(results)
    return {
        "total_evals": len(results),
        "passed": passed,
        "failed": len(results) - passed,
        "avg_score": round(avg_score, 3),
    }
