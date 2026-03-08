from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.organizations import router as org_router
from app.api.v1.users import router as users_router
from app.api.v1.roles import router as roles_router
from app.api.v1.projects import router as projects_router
from app.api.v1.phases import router as phases_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.sources import router as sources_router
from app.api.v1.agents import router as agents_router
from app.api.v1.documents import router as documents_router
from app.api.v1.questions import router as questions_router
from app.api.v1.feedback_api import router as feedback_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.evals import router as evals_router
from app.api.v1.costs import router as costs_router
from app.api.v1.improvements import router as improvements_router
from app.api.v1.knowledge import router as knowledge_router
from app.api.v1.workflow import router as workflow_router
from app.api.v1.audit import router as audit_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth_router)
api_router.include_router(org_router)
api_router.include_router(users_router)
api_router.include_router(roles_router)
api_router.include_router(projects_router)
api_router.include_router(phases_router)
api_router.include_router(tasks_router)
api_router.include_router(sources_router)
api_router.include_router(agents_router)
api_router.include_router(documents_router)
api_router.include_router(questions_router)
api_router.include_router(feedback_router)
api_router.include_router(notifications_router)
api_router.include_router(evals_router)
api_router.include_router(costs_router)
api_router.include_router(improvements_router)
api_router.include_router(knowledge_router)
api_router.include_router(workflow_router)
api_router.include_router(audit_router)
