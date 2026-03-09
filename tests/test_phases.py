"""Tests for phase endpoints: /api/v1/phases/*"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase import PhaseDefinition, PhaseInstance
from app.models.task import TaskInstance
from app.services.phase import evaluate_gate


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListPhaseDefinitions:
    async def test_list_phase_definitions(
        self,
        client: AsyncClient,
        sample_phase_def,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/phases/definitions returns all active phase definitions."""
        resp = await client.get(
            "/api/v1/phases/definitions", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert body[0]["name"] == "Discovery"


class TestListProjectPhases:
    async def test_list_project_phases(
        self,
        client: AsyncClient,
        sample_project,
        sample_phase_instance,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/phases/project/{project_id} returns phase instances."""
        resp = await client.get(
            f"/api/v1/phases/project/{sample_project.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert body[0]["project_id"] == str(sample_project.id)


class TestGetPhaseDetail:
    async def test_get_phase_detail(
        self,
        client: AsyncClient,
        sample_phase_instance,
        sample_task_instance,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/phases/{phase_instance_id} returns phase with tasks."""
        resp = await client.get(
            f"/api/v1/phases/{sample_phase_instance.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(sample_phase_instance.id)
        assert body["phase_name"] == "Discovery"
        assert body["phase_number"] == 1
        assert isinstance(body["task_instances"], list)
        assert len(body["task_instances"]) >= 1

    async def test_get_phase_not_found(
        self, client: AsyncClient, sample_user, auth_headers
    ):
        """GET /api/v1/phases/{random_id} returns 404."""
        resp = await client.get(
            f"/api/v1/phases/{uuid.uuid4()}", headers=auth_headers
        )
        assert resp.status_code == 404


class TestEvaluateGate:
    async def test_evaluate_gate(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_phase_instance,
        sample_task_instance,
        sample_user,
        auth_headers,
    ):
        """POST /api/v1/phases/{id}/evaluate-gate returns gate results."""
        # Complete the task so the gate check can evaluate
        sample_task_instance.status = "COMPLETED"
        sample_task_instance.completed_at = datetime.now(timezone.utc)
        sample_task_instance.completed_by = sample_user.id
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/phases/{sample_phase_instance.id}/evaluate-gate",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "gate_passed" in body
        assert "completed_tasks" in body
        assert body["total_tasks"] == 1
        assert body["completed_tasks"] == 1

    async def test_evaluate_gate_fails_with_incomplete_tasks(
        self,
        client: AsyncClient,
        sample_phase_instance,
        sample_task_instance,
        sample_user,
        auth_headers,
    ):
        """Gate evaluation returns gate_passed=False when tasks are incomplete."""
        resp = await client.post(
            f"/api/v1/phases/{sample_phase_instance.id}/evaluate-gate",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["gate_passed"] is False


class TestAdvancePhase:
    async def test_advance_phase(
        self,
        db_session: AsyncSession,
        sample_project,
        sample_phase_instance,
        sample_task_instance,
        sample_phase_def,
        sample_phase_def_2,
        sample_user,
        admin_role,
    ):
        """advance_phase moves the project to the next phase when gate passes."""
        from app.models.phase import PhaseInstance
        from app.models.role import UserProjectRole
        from app.services.phase import advance_phase

        # Create phase 2 instance
        pi2 = PhaseInstance(
            id=uuid.uuid4(),
            project_id=sample_project.id,
            phase_definition_id=sample_phase_def_2.id,
            status="NOT_STARTED",
        )
        db_session.add(pi2)
        await db_session.flush()

        # Complete the task
        sample_task_instance.status = "COMPLETED"
        sample_task_instance.completed_at = datetime.now(timezone.utc)
        sample_task_instance.completed_by = sample_user.id
        await db_session.flush()

        # Grant role
        upr = UserProjectRole(
            user_id=sample_user.id,
            project_id=sample_project.id,
            role_id=admin_role.id,
            assigned_by=sample_user.id,
        )
        db_session.add(upr)
        await db_session.flush()

        result = await advance_phase(db_session, sample_project.id, sample_user.id)
        assert result["next_phase"] is not None
        assert result["current_phase"].status == "COMPLETED"
        assert result["next_phase"].status == "IN_PROGRESS"


class TestRollbackPhase:
    async def test_rollback_phase(
        self,
        db_session: AsyncSession,
        sample_project,
        sample_phase_instance,
        sample_task_instance,
        sample_user,
    ):
        """rollback_phase resets the current phase and its tasks."""
        from app.services.phase import rollback_phase

        # Mark phase as IN_PROGRESS and task as COMPLETED
        sample_task_instance.status = "COMPLETED"
        sample_task_instance.completed_at = datetime.now(timezone.utc)
        await db_session.flush()

        result = await rollback_phase(db_session, sample_project.id, sample_user.id)
        assert result.status == "NOT_STARTED"
        assert result.started_at is None
        assert result.gate_results is None

        # Verify task was also reset
        await db_session.refresh(sample_task_instance)
        assert sample_task_instance.status == "NOT_STARTED"
        assert sample_task_instance.completed_at is None


class TestGateEvaluationService:
    async def test_evaluate_gate_service_level(
        self,
        db_session: AsyncSession,
        sample_phase_instance,
        sample_task_instance,
        sample_user,
    ):
        """Service-level: evaluate_gate returns structured gate results."""
        result = await evaluate_gate(db_session, sample_phase_instance.id)
        assert "gate_passed" in result
        assert "gate_results" in result
        assert "total_tasks" in result
        assert result["total_tasks"] == 1
        assert result["completed_tasks"] == 0
        assert result["gate_passed"] is False

    async def test_evaluate_gate_passes_when_all_tasks_done(
        self,
        db_session: AsyncSession,
        sample_phase_instance,
        sample_task_instance,
        sample_user,
    ):
        """Service-level: gate passes when all tasks are completed and criteria met."""
        sample_task_instance.status = "COMPLETED"
        sample_task_instance.completed_at = datetime.now(timezone.utc)
        sample_task_instance.completed_by = sample_user.id
        await db_session.flush()

        result = await evaluate_gate(db_session, sample_phase_instance.id)
        assert result["completed_tasks"] == 1
        assert result["total_tasks"] == 1
        # gate_passed depends on gate_criteria — the all_tasks_completed criterion
        # should pass since 1/1 tasks are done
        assert result["gate_passed"] is True

    async def test_evaluate_gate_not_found(
        self,
        db_session: AsyncSession,
    ):
        """Service-level: evaluate_gate raises ValueError for non-existent phase."""
        with pytest.raises(ValueError, match="Phase instance not found"):
            await evaluate_gate(db_session, uuid.uuid4())


class TestPhaseDefinitionDetail:
    async def test_phase_definition_detail_via_list(
        self,
        client: AsyncClient,
        sample_phase_def,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/phases/definitions returns definition with gate_criteria."""
        resp = await client.get(
            "/api/v1/phases/definitions", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        found = [d for d in body if d["id"] == str(sample_phase_def.id)]
        assert len(found) == 1
        detail = found[0]
        assert detail["name"] == "Discovery"
        assert detail["phase_number"] == 1
        assert detail["is_active"] is True
        assert "gate_criteria" in detail
        assert detail["gate_criteria"]["all_tasks_completed"]["required"] is True
