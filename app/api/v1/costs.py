"""Cost tracking endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import require_permission
from app.models.user import User
from app.models.cost import CostTracking

router = APIRouter(prefix="/costs", tags=["costs"])


@router.get("/project/{project_id}")
async def get_project_costs(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("view_cost_tracking"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(
            func.coalesce(func.sum(CostTracking.cost_usd), 0).label("total_cost"),
            func.coalesce(func.sum(CostTracking.tokens_input), 0).label("total_tokens_input"),
            func.coalesce(func.sum(CostTracking.tokens_output), 0).label("total_tokens_output"),
            func.count(CostTracking.id).label("total_entries"),
            func.coalesce(func.sum(case((CostTracking.is_rework == True, 1), else_=0)), 0).label("rework_count"),  # noqa: E712
            func.coalesce(func.sum(case((CostTracking.is_eval == True, 1), else_=0)), 0).label("eval_count"),  # noqa: E712
        )
        .where(CostTracking.project_id == project_id)
    )
    row = result.one()
    return {
        "project_id": str(project_id),
        "total_cost_usd": float(row.total_cost),
        "total_tokens_input": int(row.total_tokens_input),
        "total_tokens_output": int(row.total_tokens_output),
        "total_entries": int(row.total_entries),
        "rework_count": int(row.rework_count),
        "eval_count": int(row.eval_count),
    }
