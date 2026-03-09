"""Tests for authentication endpoints: /api/v1/auth/*"""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLogin:
    async def test_login_success(self, client: AsyncClient, sample_user):
        """POST /api/v1/auth/login with valid credentials returns tokens."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "testuser@example.com", "password": "testpass123"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, sample_user):
        """POST /api/v1/auth/login with wrong password returns 401."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "testuser@example.com", "password": "wrongpassword"},
        )
        assert resp.status_code == 401
        assert resp.json()["detail"] == "Invalid credentials"

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """POST /api/v1/auth/login with unknown email returns 401."""
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "nobody@example.com", "password": "whatever"},
        )
        assert resp.status_code == 401

    async def test_login_inactive_user(
        self, client: AsyncClient, db_session: AsyncSession, sample_org
    ):
        """POST /api/v1/auth/login with inactive user returns 401."""
        from app.models.user import User

        user = User(
            id=uuid.uuid4(),
            organization_id=sample_org.id,
            email="inactive@example.com",
            name="Inactive",
            hashed_password=hash_password("pass123"),
            is_active=False,
        )
        db_session.add(user)
        await db_session.flush()

        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": "inactive@example.com", "password": "pass123"},
        )
        assert resp.status_code == 401
        assert "disabled" in resp.json()["detail"].lower()


class TestProtectedRoutes:
    async def test_access_protected_route_without_token(self, client: AsyncClient):
        """GET /api/v1/auth/me without Authorization header returns 401."""
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    async def test_access_protected_route_with_token(
        self, client: AsyncClient, sample_user, auth_headers
    ):
        """GET /api/v1/auth/me with valid token returns user data."""
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "testuser@example.com"

    async def test_access_protected_route_with_bad_token(self, client: AsyncClient):
        """GET /api/v1/auth/me with a garbage token returns 401."""
        resp = await client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer bad.token.value"},
        )
        assert resp.status_code == 401


class TestGetMe:
    async def test_get_me(self, client: AsyncClient, sample_user, auth_headers):
        """GET /api/v1/auth/me returns the authenticated user's profile."""
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == str(sample_user.id)
        assert body["name"] == "Test User"
        assert body["email"] == "testuser@example.com"
        assert body["organization_id"] == str(sample_user.organization_id)
        assert body["is_active"] is True
