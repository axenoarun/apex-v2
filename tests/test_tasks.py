"""Tests for task endpoints and service: /api/v1/tasks/*"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import TaskInstance, TaskDefinition


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListTaskDefinitions:
    async def test_list_task_definitions(
        self,
        client: AsyncClient,
        sample_task_def,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/tasks/definitions returns all task definitions."""
        resp = await client.get(
            "/api/v1/tasks/definitions", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert body[0]["name"] == "Discovery Questionnaire"
        assert body[0]["classification"] == "HYBRID"

    async def test_list_task_definitions_filter_by_phase(
        self,
        client: AsyncClient,
        sample_task_def,
        sample_phase_def,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/tasks/definitions?phase_definition_id=... filters by phase."""
        resp = await client.get(
            f"/api/v1/tasks/definitions?phase_definition_id={sample_phase_def.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert all(
            t["phase_definition_id"] == str(sample_phase_def.id) for t in body
        )


class TestListTasks:
    async def test_list_tasks(
        self,
        client: AsyncClient,
        sample_task_instance,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/tasks/ returns task instances."""
        resp = await client.get("/api/v1/tasks/", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1

    async def test_list_tasks_filter_by_project(
        self,
        client: AsyncClient,
        sample_task_instance,
        sample_project,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/tasks/?project_id=... filters by project."""
        resp = await client.get(
            f"/api/v1/tasks/?project_id={sample_project.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert all(t["project_id"] == str(sample_project.id) for t in body)


class TestGetTask:
    async def test_get_task(
        self,
        client: AsyncClient,
        sample_task_instance,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/tasks/{id} returns task detail with definition info."""
        resp = await client.get(
            f"/api/v1/tasks/{sample_task_instance.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(sample_task_instance.id)
        assert body["task_name"] == "Discovery Questionnaire"
        assert body["status"] == "NOT_STARTED"

    async def test_get_task_not_found(
        self, client: AsyncClient, sample_user, auth_headers
    ):
        """GET /api/v1/tasks/{random_id} returns 404."""
        resp = await client.get(
            f"/api/v1/tasks/{uuid.uuid4()}", headers=auth_headers
        )
        assert resp.status_code == 404


class TestUpdateTaskStatus:
    async def test_update_task_status(
        self,
        client: AsyncClient,
        sample_task_instance,
        sample_user,
        auth_headers,
    ):
        """PUT /api/v1/tasks/{id} updates task fields."""
        resp = await client.put(
            f"/api/v1/tasks/{sample_task_instance.id}",
            json={"priority": "HIGH"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["priority"] == "HIGH"


class TestCompleteTask:
    async def test_complete_task(
        self,
        db_session: AsyncSession,
        sample_task_instance,
        sample_user,
        admin_role,
    ):
        """complete_task service sets status to COMPLETED."""
        from app.models.role import UserProjectRole
        from app.services.task import complete_task

        # Grant role for audit log
        from app.models.project import Project

        upr = UserProjectRole(
            user_id=sample_user.id,
            project_id=sample_task_instance.project_id,
            role_id=admin_role.id,
            assigned_by=sample_user.id,
        )
        db_session.add(upr)
        await db_session.flush()

        result = await complete_task(
            db_session,
            sample_task_instance.id,
            sample_user.id,
            ai_output={"result": "done"},
        )
        assert result.status == "COMPLETED"
        assert result.completed_at is not None
        assert result.completed_by == sample_user.id
        assert result.ai_output == {"result": "done"}


class TestAssignTask:
    async def test_assign_task(
        self,
        db_session: AsyncSession,
        sample_task_instance,
        sample_user,
        sample_org,
    ):
        """assign_task service changes the assignee."""
        from app.core.security import hash_password
        from app.models.user import User
        from app.services.task import assign_task

        new_user = User(
            id=uuid.uuid4(),
            organization_id=sample_org.id,
            email="newuser@example.com",
            name="New User",
            hashed_password=hash_password("pass"),
            is_active=True,
        )
        db_session.add(new_user)
        await db_session.flush()

        result = await assign_task(
            db_session,
            sample_task_instance.id,
            new_user.id,
            sample_user.id,
        )
        assert result.assigned_to == new_user.id
        assert result.assigned_by == "ARCHITECT"


class TestTaskDependencies:
    async def test_task_dependency_blocks_start(
        self,
        db_session: AsyncSession,
        sample_project,
        sample_phase_instance,
        sample_task_def,
        sample_user,
    ):
        """Attempting to start a task with unmet deps raises ValueError."""
        from app.services.task import update_task_instance

        # Create the blocker task
        blocker = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=sample_task_def.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="NOT_STARTED",
            trust_level="SUPERVISED",
            classification="AI",
            priority="MEDIUM",
        )
        db_session.add(blocker)
        await db_session.flush()

        # Create the dependent task
        dependent = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=sample_task_def.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="NOT_STARTED",
            trust_level="SUPERVISED",
            classification="AI",
            priority="MEDIUM",
            depends_on=[str(blocker.id)],
        )
        db_session.add(dependent)
        await db_session.flush()

        with pytest.raises(ValueError, match="blocking dependencies"):
            await update_task_instance(
                db_session, dependent.id, sample_user.id, status="IN_PROGRESS"
            )

    async def test_task_dependency_check(
        self,
        db_session: AsyncSession,
        sample_project,
        sample_phase_instance,
        sample_task_def,
        sample_user,
    ):
        """check_dependencies returns all_met=True when deps are completed."""
        from app.services.task import check_dependencies

        dep = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=sample_task_def.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="COMPLETED",
            trust_level="SUPERVISED",
            classification="AI",
            priority="MEDIUM",
            completed_at=datetime.now(timezone.utc),
            completed_by=sample_user.id,
        )
        db_session.add(dep)
        await db_session.flush()

        task = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=sample_task_def.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="NOT_STARTED",
            trust_level="SUPERVISED",
            classification="AI",
            priority="MEDIUM",
            depends_on=[str(dep.id)],
        )
        db_session.add(task)
        await db_session.flush()

        result = await check_dependencies(db_session, task)
        assert result["all_met"] is True
        assert result["blocking"] == []
        assert result["total"] == 1
        assert result["completed"] == 1

    async def test_complete_task_unblocks_dependents(
        self,
        db_session: AsyncSession,
        sample_project,
        sample_phase_instance,
        sample_task_def,
        sample_user,
    ):
        """Completing a task unblocks downstream tasks whose deps are now met."""
        from app.services.task import complete_task

        blocker = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=sample_task_def.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="IN_PROGRESS",
            trust_level="SUPERVISED",
            classification="AI",
            priority="MEDIUM",
        )
        db_session.add(blocker)
        await db_session.flush()

        dependent = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=sample_task_def.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="BLOCKED",
            trust_level="SUPERVISED",
            classification="AI",
            priority="MEDIUM",
            depends_on=[str(blocker.id)],
        )
        db_session.add(dependent)
        await db_session.flush()

        await complete_task(db_session, blocker.id, sample_user.id)

        await db_session.refresh(dependent)
        assert dependent.status == "NOT_STARTED"

    async def test_task_no_dependencies_all_met(
        self,
        db_session: AsyncSession,
        sample_task_instance,
    ):
        """A task with no depends_on has all_met=True."""
        from app.services.task import check_dependencies

        result = await check_dependencies(db_session, sample_task_instance)
        assert result["all_met"] is True
        assert result["total"] == 0


class TestTaskFilterByStatus:
    async def test_filter_tasks_by_status(
        self,
        client: AsyncClient,
        sample_task_instance,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/tasks/?status=NOT_STARTED filters correctly."""
        resp = await client.get(
            "/api/v1/tasks/?status=NOT_STARTED",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert all(t["status"] == "NOT_STARTED" for t in body)

    async def test_filter_tasks_by_status_no_results(
        self,
        client: AsyncClient,
        sample_task_instance,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/tasks/?status=COMPLETED returns empty when none completed."""
        resp = await client.get(
            "/api/v1/tasks/?status=COMPLETED",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body == []


class TestUpdateTaskStatusTransition:
    async def test_update_task_not_started_to_in_progress(
        self,
        client: AsyncClient,
        sample_task_instance,
        sample_user,
        auth_headers,
    ):
        """PUT /api/v1/tasks/{id} transitions NOT_STARTED to IN_PROGRESS."""
        resp = await client.put(
            f"/api/v1/tasks/{sample_task_instance.id}",
            json={"status": "IN_PROGRESS"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "IN_PROGRESS"
        assert body["started_at"] is not None
