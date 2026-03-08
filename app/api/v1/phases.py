"""Phase instance lifecycle endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user, require_permission, check_project_permission
from app.models.user import User
from app.models.phase import PhaseDefinition, PhaseInstance
from app.schemas.phase import (
    PhaseDefinitionResponse,
    PhaseInstanceResponse,
    PhaseInstanceDetail,
    PhaseGateOverride,
    PhaseAdvanceResponse,
)
from app.schemas.task import TaskInstanceResponse
from app.services.phase import (
    get_phase_instances,
    get_phase_instance_detail,
    get_phase_task_instances,
    evaluate_gate,
    advance_phase,
    rollback_phase,
)

router = APIRouter(prefix="/phases", tags=["phases"])


@router.get("/definitions", response_model=list[PhaseDefinitionResponse])
async def list_phase_definitions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(PhaseDefinition).order_by(PhaseDefinition.phase_number)
    )
    return list(result.scalars().all())


@router.get("/project/{project_id}", response_model=list[PhaseInstanceResponse])
async def list_project_phases(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await get_phase_instances(db, project_id)


@router.get("/{phase_instance_id}", response_model=PhaseInstanceDetail)
async def get_phase(
    phase_instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    phase = await get_phase_instance_detail(db, phase_instance_id)
    if not phase:
        raise HTTPException(status_code=404, detail="Phase instance not found")

    # Load definition for name/number
    phase_def = await db.execute(
        select(PhaseDefinition).where(PhaseDefinition.id == phase.phase_definition_id)
    )
    pd = phase_def.scalar_one()

    # Load task instances
    tasks = await get_phase_task_instances(db, phase_instance_id)

    return PhaseInstanceDetail(
        **{c.key: getattr(phase, c.key) for c in phase.__table__.columns},
        phase_name=pd.name,
        phase_number=pd.phase_number,
        task_instances=[TaskInstanceResponse.model_validate(t) for t in tasks],
    )


@router.post("/{phase_instance_id}/evaluate-gate")
async def evaluate_phase_gate(
    phase_instance_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await evaluate_gate(db, phase_instance_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/project/{project_id}/advance", response_model=PhaseAdvanceResponse)
async def advance_project_phase(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(require_permission("sign_off_gate"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await advance_phase(db, project_id, current_user.id)
        return PhaseAdvanceResponse(
            current_phase=PhaseInstanceResponse.model_validate(result["current_phase"]),
            next_phase=PhaseInstanceResponse.model_validate(result["next_phase"]) if result["next_phase"] else None,
            message=result["message"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/project/{project_id}/advance-override", response_model=PhaseAdvanceResponse)
async def override_advance_phase(
    project_id: uuid.UUID,
    body: PhaseGateOverride,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not await check_project_permission(db, current_user.id, project_id, "override_gate"):
        raise HTTPException(status_code=403, detail="Permission denied: override_gate")
    try:
        result = await advance_phase(
            db, project_id, current_user.id, override=True, override_reason=body.reason
        )
        return PhaseAdvanceResponse(
            current_phase=PhaseInstanceResponse.model_validate(result["current_phase"]),
            next_phase=PhaseInstanceResponse.model_validate(result["next_phase"]) if result["next_phase"] else None,
            message=result["message"],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/project/{project_id}/rollback", response_model=PhaseInstanceResponse)
async def rollback_project_phase(
    project_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    if not await check_project_permission(db, current_user.id, project_id, "override_gate"):
        raise HTTPException(status_code=403, detail="Permission denied: override_gate")
    try:
        return await rollback_phase(db, project_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
