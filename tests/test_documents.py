"""Tests for document endpoints: /api/v1/documents/*"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestListDocumentTemplates:
    async def test_list_document_templates(
        self,
        client: AsyncClient,
        sample_doc_template,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/documents/templates returns templates."""
        resp = await client.get(
            "/api/v1/documents/templates", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert body[0]["name"] == "Solution Design Record"

    async def test_list_document_templates_filter_by_phase(
        self,
        client: AsyncClient,
        sample_doc_template,
        sample_phase_def,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/documents/templates?phase_definition_id=... filters correctly."""
        resp = await client.get(
            f"/api/v1/documents/templates?phase_definition_id={sample_phase_def.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert all(
            t["phase_definition_id"] == str(sample_phase_def.id) for t in body
        )


class TestCreateDocument:
    async def test_create_document(
        self,
        client: AsyncClient,
        sample_doc_template,
        sample_project,
        sample_phase_instance,
        sample_user,
        auth_headers,
    ):
        """POST /api/v1/documents/ creates a document instance."""
        resp = await client.post(
            "/api/v1/documents/",
            json={
                "document_template_id": str(sample_doc_template.id),
                "project_id": str(sample_project.id),
                "phase_instance_id": str(sample_phase_instance.id),
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["status"] == "NOT_STARTED"
        assert body["generated_by"] == "AI"
        assert body["version"] == 1
        assert body["document_template_id"] == str(sample_doc_template.id)
        assert body["project_id"] == str(sample_project.id)


class TestListProjectDocuments:
    async def test_list_project_documents(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_doc_template,
        sample_project,
        sample_phase_instance,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/documents/project/{id} returns documents for a project."""
        from app.models.document import DocumentInstance

        doc = DocumentInstance(
            id=uuid.uuid4(),
            document_template_id=sample_doc_template.id,
            project_id=sample_project.id,
            phase_instance_id=sample_phase_instance.id,
            status="DRAFT",
            generated_by="AI",
            version=1,
        )
        db_session.add(doc)
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/documents/project/{sample_project.id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert isinstance(body, list)
        assert len(body) >= 1
        assert body[0]["project_id"] == str(sample_project.id)


class TestReviewDocument:
    async def test_review_document_approve(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_doc_template,
        sample_project,
        sample_phase_instance,
        sample_user,
        auth_headers,
    ):
        """POST /api/v1/documents/{id}/review with approved=true sets FINAL."""
        from app.models.document import DocumentInstance

        doc = DocumentInstance(
            id=uuid.uuid4(),
            document_template_id=sample_doc_template.id,
            project_id=sample_project.id,
            phase_instance_id=sample_phase_instance.id,
            status="IN_REVIEW",
            generated_by="AI",
            version=1,
        )
        db_session.add(doc)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/documents/{doc.id}/review",
            json={"approved": True},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "FINAL"
        assert body["reviewed_by"] == str(sample_user.id)
        assert body["version"] == 2  # version incremented on approval

    async def test_review_document_reject(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_doc_template,
        sample_project,
        sample_phase_instance,
        sample_user,
        auth_headers,
    ):
        """POST /api/v1/documents/{id}/review with approved=false sets REVISION_REQUESTED."""
        from app.models.document import DocumentInstance

        doc = DocumentInstance(
            id=uuid.uuid4(),
            document_template_id=sample_doc_template.id,
            project_id=sample_project.id,
            phase_instance_id=sample_phase_instance.id,
            status="IN_REVIEW",
            generated_by="AI",
            version=1,
        )
        db_session.add(doc)
        await db_session.flush()

        resp = await client.post(
            f"/api/v1/documents/{doc.id}/review",
            json={"approved": False},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "REVISION_REQUESTED"
        assert body["version"] == 1  # version NOT incremented on rejection


class TestGetDocumentTemplateDetail:
    async def test_get_template_detail_via_list(
        self,
        client: AsyncClient,
        sample_doc_template,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/documents/templates returns template with full detail."""
        resp = await client.get(
            "/api/v1/documents/templates", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        found = [t for t in body if t["id"] == str(sample_doc_template.id)]
        assert len(found) == 1
        detail = found[0]
        assert detail["name"] == "Solution Design Record"
        assert detail["output_format"] == "DOCX"
        assert detail["ai_generation_prompt"] == "Generate an SDR document."
        assert detail["template_structure"] == {"sections": ["overview", "architecture"]}


class TestUpdateDocumentInstance:
    async def test_update_document_instance_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_doc_template,
        sample_project,
        sample_phase_instance,
        sample_user,
        auth_headers,
    ):
        """PUT /api/v1/documents/{id} updates document status."""
        from app.models.document import DocumentInstance

        doc = DocumentInstance(
            id=uuid.uuid4(),
            document_template_id=sample_doc_template.id,
            project_id=sample_project.id,
            phase_instance_id=sample_phase_instance.id,
            status="DRAFT",
            generated_by="AI",
            version=1,
        )
        db_session.add(doc)
        await db_session.flush()

        resp = await client.put(
            f"/api/v1/documents/{doc.id}",
            json={"status": "IN_REVIEW"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "IN_REVIEW"

    async def test_update_document_instance_content(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_doc_template,
        sample_project,
        sample_phase_instance,
        sample_user,
        auth_headers,
    ):
        """PUT /api/v1/documents/{id} updates document content."""
        from app.models.document import DocumentInstance

        doc = DocumentInstance(
            id=uuid.uuid4(),
            document_template_id=sample_doc_template.id,
            project_id=sample_project.id,
            phase_instance_id=sample_phase_instance.id,
            status="DRAFT",
            generated_by="HUMAN",
            version=1,
        )
        db_session.add(doc)
        await db_session.flush()

        new_content = {"sections": {"overview": "Updated overview"}}
        resp = await client.put(
            f"/api/v1/documents/{doc.id}",
            json={"content": new_content},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["content"] == new_content

    async def test_update_document_not_found(
        self,
        client: AsyncClient,
        sample_user,
        auth_headers,
    ):
        """PUT /api/v1/documents/{random_id} returns 404."""
        resp = await client.put(
            f"/api/v1/documents/{uuid.uuid4()}",
            json={"status": "DRAFT"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestGetDocument:
    async def test_get_document_instance(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        sample_doc_template,
        sample_project,
        sample_phase_instance,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/documents/{id} returns the document instance."""
        from app.models.document import DocumentInstance

        doc = DocumentInstance(
            id=uuid.uuid4(),
            document_template_id=sample_doc_template.id,
            project_id=sample_project.id,
            phase_instance_id=sample_phase_instance.id,
            status="DRAFT",
            generated_by="AI",
            version=1,
            content={"sections": {"overview": "test"}},
        )
        db_session.add(doc)
        await db_session.flush()

        resp = await client.get(
            f"/api/v1/documents/{doc.id}", headers=auth_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(doc.id)
        assert body["status"] == "DRAFT"
        assert body["content"]["sections"]["overview"] == "test"

    async def test_get_document_not_found(
        self,
        client: AsyncClient,
        sample_user,
        auth_headers,
    ):
        """GET /api/v1/documents/{random_id} returns 404."""
        resp = await client.get(
            f"/api/v1/documents/{uuid.uuid4()}", headers=auth_headers
        )
        assert resp.status_code == 404
