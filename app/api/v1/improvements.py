"""Improvement proposal endpoints."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models.user import User
from app.schemas.improvement import (
    ImprovementProposalCreate,
    ImprovementProposalResponse,
    ImprovementReviewRequest,
)
from app.services.improvement import create_proposal, review_proposal, list_proposals

router = APIRouter(prefix="/improvements", tags=["improvements"])


@router.post("/", response_model=ImprovementProposalResponse, status_code=status.HTTP_201_CREATED)
async def create_improvement(
    body: ImprovementProposalCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_proposal(db, **body.model_dump())


@router.get("/", response_model=list[ImprovementProposalResponse])
async def list_improvements(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: uuid.UUID | None = Query(None),
    proposal_status: str | None = Query(None, alias="status"),
):
    return await list_proposals(db, project_id=project_id, status=proposal_status)


@router.post("/{proposal_id}/review", response_model=ImprovementProposalResponse)
async def review_improvement(
    proposal_id: uuid.UUID,
    body: ImprovementReviewRequest,
    current_user: Annotated[User, Depends(require_permission("review_improvements"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await review_proposal(db, proposal_id, current_user.id, body.status)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
