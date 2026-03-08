"""Agent definition + execution endpoints — includes AI task execution triggers."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.deps import get_current_user, require_permission
from app.models.user import User
from app.models.task import TaskInstance, TaskDefinition
from app.schemas.agent import (
    AgentDefinitionResponse,
    AgentExecutionCreate,
    AgentExecutionResponse,
    AgentExecutionUpdate,
)
from app.services.agent import (
    list_agent_definitions,
    create_execution,
    complete_execution,
    pause_execution,
    list_executions,
    get_execution,
)

router = APIRouter(prefix="/agents", tags=["agents"])


# --- Request models ---

class ExecuteTaskRequest(BaseModel):
    task_instance_id: uuid.UUID
    async_mode: bool = True  # True = Celery background, False = inline


class ResumeExecutionRequest(BaseModel):
    additional_input: dict


class GenerateQuestionsRequest(BaseModel):
    project_id: uuid.UUID
    phase_instance_id: uuid.UUID
    async_mode: bool = True


class GenerateDocumentRequest(BaseModel):
    project_id: uuid.UUID
    template_id: uuid.UUID
    phase_instance_id: uuid.UUID
    task_instance_id: uuid.UUID | None = None
    async_mode: bool = True


class AnalyzeFeedbackRequest(BaseModel):
    project_id: uuid.UUID


class ExtractKnowledgeRequest(BaseModel):
    project_id: uuid.UUID


class TrustAdjustmentRequest(BaseModel):
    project_id: uuid.UUID


# --- Existing CRUD endpoints ---

@router.get("/definitions", response_model=list[AgentDefinitionResponse])
async def get_agent_definitions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await list_agent_definitions(db)


@router.post("/executions", response_model=AgentExecutionResponse, status_code=status.HTTP_201_CREATED)
async def create_agent_execution(
    body: AgentExecutionCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    return await create_execution(
        db,
        agent_definition_id=body.agent_definition_id,
        project_id=body.project_id,
        task_instance_id=body.task_instance_id,
        triggered_by=body.triggered_by,
        input_context=body.input_context,
    )


@router.get("/executions", response_model=list[AgentExecutionResponse])
async def list_agent_executions(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    project_id: uuid.UUID | None = Query(None),
    task_instance_id: uuid.UUID | None = Query(None),
    agent_definition_id: uuid.UUID | None = Query(None),
    exec_status: str | None = Query(None, alias="status"),
):
    return await list_executions(
        db,
        project_id=project_id,
        task_instance_id=task_instance_id,
        agent_definition_id=agent_definition_id,
        status=exec_status,
    )


@router.get("/executions/{execution_id}", response_model=AgentExecutionResponse)
async def get_agent_execution(
    execution_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    execution = await get_execution(db, execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Agent execution not found")
    return execution


@router.post("/executions/{execution_id}/pause", response_model=AgentExecutionResponse)
async def pause_agent_execution(
    execution_id: uuid.UUID,
    body: AgentExecutionUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        return await pause_execution(db, execution_id, body.pause_reason or {})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# --- AI Execution Endpoints ---

@router.post("/execute-task", response_model=dict)
async def execute_task(
    body: ExecuteTaskRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Trigger AI execution for a task instance.

    Per Rule 5.3: executes AI or HYBRID tasks based on trust level.
    """
    # Validate task exists
    result = await db.execute(
        select(TaskInstance, TaskDefinition)
        .join(TaskDefinition, TaskInstance.task_definition_id == TaskDefinition.id)
        .where(TaskInstance.id == body.task_instance_id)
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Task instance not found")

    task_instance, task_def = row

    if task_def.classification == "MANUAL":
        raise HTTPException(status_code=400, detail="Cannot execute AI on a MANUAL task")

    if task_instance.status not in ("NOT_STARTED", "WAITING_INPUT", "AI_PAUSED_NEEDS_INPUT"):
        raise HTTPException(
            status_code=400,
            detail=f"Task is in status '{task_instance.status}' and cannot be executed",
        )

    if body.async_mode:
        from app.worker import execute_ai_task_bg
        task = execute_ai_task_bg.delay(str(body.task_instance_id), f"USER:{current_user.id}")
        return {"celery_task_id": task.id, "status": "QUEUED", "message": "AI task execution queued"}
    else:
        from app.services.ai_executor import execute_ai_task
        execution = await execute_ai_task(
            task_instance, task_def, db, triggered_by=f"USER:{current_user.id}"
        )
        return {
            "execution_id": str(execution.id),
            "status": execution.status,
            "confidence_score": execution.confidence_score,
        }


@router.post("/executions/{execution_id}/resume", response_model=dict)
async def resume_execution(
    execution_id: uuid.UUID,
    body: ResumeExecutionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Resume a paused AI execution with additional input. Per Rule 5.4."""
    from app.services.ai_executor import resume_paused_execution

    try:
        execution = await resume_paused_execution(execution_id, body.additional_input, db)
        return {
            "execution_id": str(execution.id),
            "status": execution.status,
            "confidence_score": execution.confidence_score,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/generate-questions", response_model=dict)
async def generate_questions(
    body: GenerateQuestionsRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generate AI questions for a phase. Per Rule 5.8."""
    if body.async_mode:
        from app.worker import generate_questions_bg
        task = generate_questions_bg.delay(str(body.project_id), str(body.phase_instance_id))
        return {"celery_task_id": task.id, "status": "QUEUED", "message": "Question generation queued"}
    else:
        from app.services.ai_questions_engine import generate_questions_for_phase
        questions = await generate_questions_for_phase(body.project_id, body.phase_instance_id, db)
        return {"questions_generated": len(questions), "status": "COMPLETED"}


@router.post("/generate-document", response_model=dict)
async def generate_document(
    body: GenerateDocumentRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Generate a document from a template using AI."""
    if body.async_mode:
        from app.worker import generate_document_bg
        task = generate_document_bg.delay(
            str(body.project_id), str(body.template_id),
            str(body.phase_instance_id),
            str(body.task_instance_id) if body.task_instance_id else None,
        )
        return {"celery_task_id": task.id, "status": "QUEUED", "message": "Document generation queued"}
    else:
        from app.services.ai_documents_engine import generate_document as gen_doc
        doc = await gen_doc(
            body.project_id, body.template_id, body.phase_instance_id, db,
            task_instance_id=body.task_instance_id,
        )
        return {"document_id": str(doc.id), "status": doc.status}


@router.post("/analyze-feedback", response_model=dict)
async def analyze_feedback(
    body: AnalyzeFeedbackRequest,
    current_user: Annotated[User, Depends(require_permission("sign_off_gate"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Analyze project feedback and generate improvement proposals. Per Section 10.2."""
    from app.worker import analyze_feedback_bg
    task = analyze_feedback_bg.delay(str(body.project_id))
    return {"celery_task_id": task.id, "status": "QUEUED", "message": "Feedback analysis queued"}


@router.post("/extract-knowledge", response_model=dict)
async def extract_knowledge(
    body: ExtractKnowledgeRequest,
    current_user: Annotated[User, Depends(require_permission("sign_off_gate"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Extract cross-project knowledge from a project. Per Section 10.4."""
    from app.worker import extract_knowledge_bg
    task = extract_knowledge_bg.delay(str(body.project_id))
    return {"celery_task_id": task.id, "status": "QUEUED", "message": "Knowledge extraction queued"}


@router.post("/trust-adjustments", response_model=dict)
async def get_trust_adjustments(
    body: TrustAdjustmentRequest,
    current_user: Annotated[User, Depends(require_permission("sign_off_gate"))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get recommended trust level adjustments based on feedback. Per Section 10.3."""
    from app.services.ai_improvements_engine import auto_adjust_trust_levels
    adjustments = await auto_adjust_trust_levels(body.project_id, db)
    return {"adjustments": adjustments, "count": len(adjustments)}


@router.get("/celery-task/{task_id}/status")
async def get_celery_task_status(
    task_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
):
    """Poll the status of a Celery background task."""
    from app.worker import celery_app

    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "error": str(result.result) if result.failed() else None,
    }
