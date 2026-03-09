"""Tests for agent endpoints: /api/v1/agents/*"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import AgentDefinition, AgentExecution
from app.models.task import TaskInstance, TaskDefinition


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListAgentDefinitions:
    async def test_list_agent_definitions(
        self,
        client: AsyncClient,
        sample_agent_def,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/agents/definitions returns active agent definitions."""
        resp = await client.get(
            "/api/v1/agents/definitions", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert body[0]["name"] == "orchestrator"
        assert body[0]["is_active"] is True


class TestGetAgentDefinitionDetail:
    async def test_get_agent_definition_detail_via_list(
        self,
        client: AsyncClient,
        sample_agent_def,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/agents/definitions returns definition with full detail."""
        resp = await client.get(
            "/api/v1/agents/definitions", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        found = [d for d in body if d["id"] == str(sample_agent_def.id)]
        assert len(found) == 1
        detail = found[0]
        assert detail["name"] == "orchestrator"
        assert detail["display_name"] == "Orchestrator Agent"
        assert detail["role_description"] == "Coordinates task execution"
        assert detail["model"] == "claude-sonnet-4-20250514"
        assert detail["temperature"] == 0.3
        assert detail["is_active"] is True


class TestCreateExecution:
    async def test_create_execution(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_agent_def,
        sample_project,
        sample_user,
        auth_headers,
    ):
        """POST /api/v1/agents/executions creates a new execution record."""
        resp = await client.post(
            "/api/v1/agents/executions",
            json={
                "agent_definition_id": str(sample_agent_def.id),
                "project_id": str(sample_project.id),
                "triggered_by": "USER:manual",
                "input_context": {"test": True},
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "PENDING"
        assert body["agent_definition_id"] == str(sample_agent_def.id)
        assert body["project_id"] == str(sample_project.id)
        assert body["tokens_input"] == 0
        assert body["tokens_output"] == 0


class TestListExecutions:
    async def test_list_executions(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_agent_def,
        sample_project,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/agents/executions returns execution records."""
        execution = AgentExecution(
            id=uuid.uuid4(),
            agent_definition_id=sample_agent_def.id,
            project_id=sample_project.id,
            triggered_by="SYSTEM",
            status="PENDING",
            tokens_input=0,
            tokens_output=0,
            cost_usd=Decimal("0"),
        )
        db_session.add(execution)
        await db_session.flush()

        resp = await client.get(
            "/api/v1/agents/executions", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1

    async def test_list_executions_filter_by_project(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_agent_def,
        sample_project,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/agents/executions?project_id=... filters correctly."""
        execution = AgentExecution(
            id=uuid.uuid4(),
            agent_definition_id=sample_agent_def.id,
            project_id=sample_project.id,
            triggered_by="SYSTEM",
            status="COMPLETED",
            tokens_input=100,
            tokens_output=50,
            cost_usd=Decimal("0.001"),
        )
        db_session.add(execution)
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/agents/executions?project_id={sample_project.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert all(e["project_id"] == str(sample_project.id) for e in body)


class TestGetExecution:
    async def test_get_execution(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_agent_def,
        sample_project,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/agents/executions/{id} returns execution detail."""
        execution = AgentExecution(
            id=uuid.uuid4(),
            agent_definition_id=sample_agent_def.id,
            project_id=sample_project.id,
            triggered_by="USER:test",
            status="PENDING",
            tokens_input=0,
            tokens_output=0,
            cost_usd=Decimal("0"),
        )
        db_session.add(execution)
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/agents/executions/{execution.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(execution.id)
        assert body["triggered_by"] == "USER:test"

    async def test_get_execution_not_found(
        self, client: AsyncClient, sample_user, auth_headers
    ):
        """GET /api/v1/agents/executions/{random_id} returns 404."""
        resp = await client.get(
            f"/api/v1/agents/executions/{uuid.uuid4()}", headers=auth_headers
        )
        assert resp.status_code == 404


class TestExecuteTaskManualRejected:
    async def test_execute_task_manual_rejected(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_project,
        sample_phase_instance,
        sample_phase_def,
        sample_user,
        auth_headers,
    ):
        """POST /api/v1/agents/execute-task rejects MANUAL tasks with 400."""
        # Create a MANUAL task definition
        td = TaskDefinition(
            id=uuid.uuid4(),
            phase_definition_id=sample_phase_def.id,
            name="Manual Review",
            classification="MANUAL",
            default_owner_role="ARCHITECT",
            default_trust_level="SUPERVISED",
            sort_order=99,
            is_active=True,
        )
        db_session.add(td)
        await db_session.flush()

        ti = TaskInstance(
            id=uuid.uuid4(),
            task_definition_id=td.id,
            phase_instance_id=sample_phase_instance.id,
            project_id=sample_project.id,
            assigned_by="AI",
            status="NOT_STARTED",
            trust_level="SUPERVISED",
            classification="MANUAL",
            priority="MEDIUM",
        )
        db_session.add(ti)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/agents/execute-task",
            json={"task_instance_id": str(ti.id), "async_mode": False},
            headers=auth_headers,
        )
        assert resp.status_code == 400
        assert "MANUAL" in resp.json()["detail"]


class TestPauseExecution:
    async def test_pause_execution(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_agent_def,
        sample_project,
        sample_user,
        auth_headers,
    ):
        """POST /api/v1/agents/executions/{id}/pause sets status to PAUSED."""
        execution = AgentExecution(
            id=uuid.uuid4(),
            agent_definition_id=sample_agent_def.id,
            project_id=sample_project.id,
            triggered_by="USER:test",
            status="IN_PROGRESS",
            tokens_input=50,
            tokens_output=25,
            cost_usd=Decimal("0.001"),
        )
        db_session.add(execution)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/agents/executions/{execution.id}/pause",
            json={"pause_reason": {"type": "LOW_CONFIDENCE", "confidence": 0.4}},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "PAUSED"
        assert body["paused"] is True
        assert body["pause_reason"]["type"] == "LOW_CONFIDENCE"
