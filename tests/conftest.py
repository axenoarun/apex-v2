"""
Shared fixtures for APEX v2 test suite.

Uses an async in-memory SQLite database so tests run without any external
services (no Postgres, no Redis, no API keys).
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import create_access_token, hash_password
from app.database import Base, get_db
from app.main import app

# ---------------------------------------------------------------------------
# SQLite compatibility: PostgreSQL types (JSONB, UUID) -> SQLite equivalents
# ---------------------------------------------------------------------------

from sqlalchemy.dialects.sqlite.base import SQLiteTypeCompiler

# JSONB -> JSON
if not hasattr(SQLiteTypeCompiler, "visit_JSONB"):
    SQLiteTypeCompiler.visit_JSONB = lambda self, type_, **kw: "JSON"

# UUID -> CHAR(36) — store as text
if not hasattr(SQLiteTypeCompiler, "visit_UUID"):
    SQLiteTypeCompiler.visit_UUID = lambda self, type_, **kw: "CHAR(36)"

# Override PostgreSQL UUID type so it stores/retrieves strings on SQLite
# instead of calling .hex on values (which fails for string UUIDs).
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
import sqlalchemy.types as _types

_orig_uuid_bind = PG_UUID.bind_processor

def _safe_uuid_bind(self, dialect):
    if dialect.name == "sqlite":
        def process(value):
            if value is not None:
                return str(value)
            return value
        return process
    return _orig_uuid_bind(self, dialect)

PG_UUID.bind_processor = _safe_uuid_bind

_orig_uuid_result = PG_UUID.result_processor

def _safe_uuid_result(self, dialect, coltype):
    if dialect.name == "sqlite":
        def process(value):
            if value is not None:
                if isinstance(value, uuid.UUID):
                    return value
                return uuid.UUID(str(value))
            return value
        return process
    return _orig_uuid_result(self, dialect, coltype)

PG_UUID.result_processor = _safe_uuid_result

# Patch Index so that postgresql_using is silently ignored on SQLite
import sqlalchemy.sql.schema as _schema
_orig_index_init = _schema.Index.__init__

def _patched_index_init(self, *args, **kwargs):
    kwargs.pop("postgresql_using", None)
    return _orig_index_init(self, *args, **kwargs)

_schema.Index.__init__ = _patched_index_init

# ---------------------------------------------------------------------------
# Engine & session factory -- in-memory SQLite via aiosqlite
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


# ---------------------------------------------------------------------------
# SQLite compatibility: enable foreign-key enforcement
# ---------------------------------------------------------------------------

@event.listens_for(engine.sync_engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


# ---------------------------------------------------------------------------
# Database session fixture (function-scoped for isolation)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Yield a fresh async session backed by a brand-new in-memory DB."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Override get_db so the FastAPI app uses our test session
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession):
    """AsyncClient wired to the test database."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="function")
async def sample_org(db_session: AsyncSession):
    """Create and return a sample Organization."""
    from app.models.organization import Organization

    org = Organization(id=uuid.uuid4(), name="Test Org")
    db_session.add(org)
    await db_session.flush()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture(scope="function")
async def sample_user(db_session: AsyncSession, sample_org):
    """Create and return a sample User with a known password."""
    from app.models.user import User

    user = User(
        id=uuid.uuid4(),
        organization_id=sample_org.id,
        email="testuser@example.com",
        name="Test User",
        hashed_password=hash_password("testpass123"),
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def admin_role(db_session: AsyncSession):
    """Create an ARCHITECT role with all required permissions."""
    from app.models.role import Role

    role = Role(
        id=uuid.uuid4(),
        name="ARCHITECT",
        description="Solution Architect",
        permissions={
            "create_project": True,
            "assign_roles": True,
            "reassign_task": True,
            "complete_task": True,
            "sign_off_gate": True,
            "override_gate": True,
        },
        is_system_role=True,
    )
    db_session.add(role)
    await db_session.flush()
    await db_session.refresh(role)
    return role


@pytest_asyncio.fixture(scope="function")
async def user_project_role(db_session: AsyncSession, sample_user, admin_role, sample_project):
    """Assign the sample user the ARCHITECT role on the sample project."""
    from app.models.role import UserProjectRole

    upr = UserProjectRole(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        project_id=sample_project.id,
        role_id=admin_role.id,
        assigned_by=sample_user.id,
    )
    db_session.add(upr)
    await db_session.flush()
    await db_session.refresh(upr)
    return upr


@pytest_asyncio.fixture(scope="function")
async def auth_headers(sample_user):
    """Return Authorization headers containing a valid JWT for sample_user."""
    token = create_access_token({"sub": str(sample_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(scope="function")
async def sample_phase_def(db_session: AsyncSession):
    """Create and return a sample PhaseDefinition."""
    from app.models.phase import PhaseDefinition

    pd = PhaseDefinition(
        id=uuid.uuid4(),
        name="Discovery",
        phase_number=1,
        description="Discovery phase",
        is_active=True,
        gate_criteria={"all_tasks_completed": {"required": True, "description": "All tasks done"}},
    )
    db_session.add(pd)
    await db_session.flush()
    await db_session.refresh(pd)
    return pd


@pytest_asyncio.fixture(scope="function")
async def sample_phase_def_2(db_session: AsyncSession):
    """Second phase definition (phase 2)."""
    from app.models.phase import PhaseDefinition

    pd = PhaseDefinition(
        id=uuid.uuid4(),
        name="Solution Design",
        phase_number=2,
        description="Solution design phase",
        is_active=True,
        gate_criteria={},
    )
    db_session.add(pd)
    await db_session.flush()
    await db_session.refresh(pd)
    return pd


@pytest_asyncio.fixture(scope="function")
async def sample_task_def(db_session: AsyncSession, sample_phase_def):
    """Create and return a sample TaskDefinition."""
    from app.models.task import TaskDefinition

    td = TaskDefinition(
        id=uuid.uuid4(),
        phase_definition_id=sample_phase_def.id,
        name="Discovery Questionnaire",
        description="Gather initial requirements",
        classification="HYBRID",
        hybrid_pattern="AI_DRAFTS_HUMAN_REVIEWS",
        default_owner_role="ARCHITECT",
        default_trust_level="SUPERVISED",
        sort_order=1,
        is_active=True,
    )
    db_session.add(td)
    await db_session.flush()
    await db_session.refresh(td)
    return td


@pytest_asyncio.fixture(scope="function")
async def sample_project(db_session: AsyncSession, sample_org, sample_user):
    """Create a bare Project (no scaffolding)."""
    from app.models.project import Project

    project = Project(
        id=uuid.uuid4(),
        organization_id=sample_org.id,
        name="Test Migration Project",
        client_name="Acme Corp",
        description="CJA migration for Acme",
        status="ACTIVE",
        created_by=sample_user.id,
    )
    db_session.add(project)
    await db_session.flush()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture(scope="function")
async def sample_phase_instance(db_session: AsyncSession, sample_project, sample_phase_def):
    """Create a PhaseInstance tied to the sample project and phase definition."""
    from app.models.phase import PhaseInstance

    pi = PhaseInstance(
        id=uuid.uuid4(),
        project_id=sample_project.id,
        phase_definition_id=sample_phase_def.id,
        status="IN_PROGRESS",
        started_at=datetime.now(timezone.utc),
    )
    db_session.add(pi)
    await db_session.flush()
    await db_session.refresh(pi)

    # Point the project at this phase
    sample_project.current_phase_id = pi.id
    await db_session.flush()

    return pi


@pytest_asyncio.fixture(scope="function")
async def sample_task_instance(
    db_session: AsyncSession,
    sample_project,
    sample_phase_instance,
    sample_task_def,
    sample_user,
):
    """Create a TaskInstance tied to sample project/phase/task-def."""
    from app.models.task import TaskInstance

    ti = TaskInstance(
        id=uuid.uuid4(),
        task_definition_id=sample_task_def.id,
        phase_instance_id=sample_phase_instance.id,
        project_id=sample_project.id,
        assigned_to=sample_user.id,
        assigned_by="AI",
        status="NOT_STARTED",
        trust_level="SUPERVISED",
        classification="HYBRID",
        priority="MEDIUM",
    )
    db_session.add(ti)
    await db_session.flush()
    await db_session.refresh(ti)
    return ti


@pytest_asyncio.fixture(scope="function")
async def sample_doc_template(db_session: AsyncSession, sample_phase_def):
    """Create a DocumentTemplate."""
    from app.models.document import DocumentTemplate

    dt = DocumentTemplate(
        id=uuid.uuid4(),
        name="Solution Design Record",
        phase_definition_id=sample_phase_def.id,
        template_structure={"sections": ["overview", "architecture"]},
        output_format="DOCX",
        ai_generation_prompt="Generate an SDR document.",
    )
    db_session.add(dt)
    await db_session.flush()
    await db_session.refresh(dt)
    return dt


@pytest_asyncio.fixture(scope="function")
async def sample_agent_def(db_session: AsyncSession):
    """Create an AgentDefinition."""
    from app.models.agent import AgentDefinition

    ad = AgentDefinition(
        id=uuid.uuid4(),
        name="orchestrator",
        display_name="Orchestrator Agent",
        role_description="Coordinates task execution",
        model="claude-sonnet-4-20250514",
        temperature=0.3,
        is_active=True,
    )
    db_session.add(ad)
    await db_session.flush()
    await db_session.refresh(ad)
    return ad
