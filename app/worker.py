"""Celery worker — background AI task execution.

Tasks:
- execute_ai_task_bg: Run AI task execution in background
- generate_questions_bg: Generate questions for a phase
- generate_document_bg: Generate a document from template
- analyze_feedback_bg: Analyze feedback and propose improvements
- extract_knowledge_bg: Extract cross-project knowledge
"""

import asyncio
import logging
import uuid

from celery import Celery

from app.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "apex",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={},
)


def _run_async(coro):
    """Run an async function from sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _get_db_session():
    """Get a database session for background tasks."""
    from app.database import async_session
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@celery_app.task(name="execute_ai_task", bind=True, max_retries=2)
def execute_ai_task_bg(self, task_instance_id: str, triggered_by: str = "SYSTEM"):
    """Execute an AI task in the background."""

    async def _run():
        from app.database import async_session
        from app.models.task import TaskInstance, TaskDefinition
        from app.services.ai_executor import execute_ai_task
        from sqlalchemy import select

        async with async_session() as db:
            try:
                result = await db.execute(
                    select(TaskInstance, TaskDefinition)
                    .join(TaskDefinition, TaskInstance.task_definition_id == TaskDefinition.id)
                    .where(TaskInstance.id == uuid.UUID(task_instance_id))
                )
                row = result.one_or_none()
                if not row:
                    logger.error(f"Task instance {task_instance_id} not found")
                    return {"error": "Task instance not found"}

                task_instance, task_def = row
                execution = await execute_ai_task(
                    task_instance, task_def, db, triggered_by=triggered_by
                )
                await db.commit()
                return {"execution_id": str(execution.id), "status": execution.status}
            except Exception as e:
                await db.rollback()
                logger.error(f"AI task execution failed: {e}")
                raise

    return _run_async(_run())


@celery_app.task(name="generate_questions", bind=True, max_retries=2)
def generate_questions_bg(self, project_id: str, phase_instance_id: str):
    """Generate questions for a phase in the background."""

    async def _run():
        from app.database import async_session
        from app.services.ai_questions_engine import generate_questions_for_phase

        async with async_session() as db:
            try:
                questions = await generate_questions_for_phase(
                    uuid.UUID(project_id), uuid.UUID(phase_instance_id), db
                )
                await db.commit()
                return {"questions_generated": len(questions)}
            except Exception as e:
                await db.rollback()
                logger.error(f"Question generation failed: {e}")
                raise

    return _run_async(_run())


@celery_app.task(name="generate_document", bind=True, max_retries=2)
def generate_document_bg(
    self,
    project_id: str,
    template_id: str,
    phase_instance_id: str,
    task_instance_id: str | None = None,
):
    """Generate a document in the background."""

    async def _run():
        from app.database import async_session
        from app.services.ai_documents_engine import generate_document

        async with async_session() as db:
            try:
                doc = await generate_document(
                    uuid.UUID(project_id),
                    uuid.UUID(template_id),
                    uuid.UUID(phase_instance_id),
                    db,
                    task_instance_id=uuid.UUID(task_instance_id) if task_instance_id else None,
                )
                await db.commit()
                return {"document_id": str(doc.id), "status": doc.status}
            except Exception as e:
                await db.rollback()
                logger.error(f"Document generation failed: {e}")
                raise

    return _run_async(_run())


@celery_app.task(name="analyze_feedback", bind=True, max_retries=1)
def analyze_feedback_bg(self, project_id: str):
    """Analyze feedback and propose improvements in the background."""

    async def _run():
        from app.database import async_session
        from app.services.ai_improvements_engine import analyze_feedback_and_propose

        async with async_session() as db:
            try:
                proposals = await analyze_feedback_and_propose(uuid.UUID(project_id), db)
                await db.commit()
                return {"proposals_generated": len(proposals)}
            except Exception as e:
                await db.rollback()
                logger.error(f"Feedback analysis failed: {e}")
                raise

    return _run_async(_run())


@celery_app.task(name="extract_knowledge", bind=True, max_retries=1)
def extract_knowledge_bg(self, project_id: str):
    """Extract cross-project knowledge in the background."""

    async def _run():
        from app.database import async_session
        from app.services.ai_improvements_engine import extract_knowledge_from_project

        async with async_session() as db:
            try:
                entries = await extract_knowledge_from_project(uuid.UUID(project_id), db)
                await db.commit()
                return {"knowledge_entries": len(entries)}
            except Exception as e:
                await db.rollback()
                logger.error(f"Knowledge extraction failed: {e}")
                raise

    return _run_async(_run())
