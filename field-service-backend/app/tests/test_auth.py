from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import UserRole
from app.tests.conftest import auth_headers, make_user

pytestmark = pytest.mark.asyncio


class TestLogin:
    async def test_valid_credentials_returns_tokens(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await make_user(db, email="login@test.com")
        response = await client.post(
            "/auth/login", json={"email": "login@test.com", "password": "Password1"}
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_wrong_password_returns_401(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        await make_user(db, email="wrong_pw@test.com")
        response = await client.post(
            "/auth/login",
            json={"email": "wrong_pw@test.com", "password": "WrongPass1"},
        )
        assert response.status_code == 401

    async def test_unknown_email_returns_401(self, client: AsyncClient) -> None:
        response = await client.post(
            "/auth/login",
            json={"email": "nobody@test.com", "password": "Password1"},
        )
        assert response.status_code == 401

    async def test_inactive_user_returns_403(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await make_user(db, email="inactive@test.com")
        user.is_active = False
        await db.flush()

        response = await client.post(
            "/auth/login",
            json={"email": "inactive@test.com", "password": "Password1"},
        )
        assert response.status_code == 403


class TestRefresh:
    async def test_valid_refresh_token_issues_new_access_token(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await make_user(db, email="refresh@test.com")
        login_resp = await client.post(
            "/auth/login",
            json={"email": "refresh@test.com", "password": "Password1"},
        )
        refresh_token = login_resp.json()["refresh_token"]

        response = await client.post(
            "/auth/refresh", json={"refresh_token": refresh_token}
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_invalid_refresh_token_returns_401(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/auth/refresh", json={"refresh_token": "not.a.valid.jwt"}
        )
        assert response.status_code == 401


class TestRegister:
    async def test_manager_can_register_new_user(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        response = await client.post(
            "/auth/register",
            json={
                "email": "newworker@test.com",
                "full_name": "New Worker",
                "password": "Password1",
                "role": "field_worker",
            },
            headers=auth_headers(manager),
        )
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "newworker@test.com"
        assert body["role"] == "field_worker"

    async def test_field_worker_cannot_register_users(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        worker = await make_user(db, role=UserRole.FIELD_WORKER)
        response = await client.post(
            "/auth/register",
            json={
                "email": "another@test.com",
                "full_name": "Another",
                "password": "Password1",
                "role": "field_worker",
            },
            headers=auth_headers(worker),
        )
        assert response.status_code == 403

    async def test_duplicate_email_returns_409(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        manager = await make_user(db, role=UserRole.MANAGER)
        existing = await make_user(db, email="dup@test.com")
        response = await client.post(
            "/auth/register",
            json={
                "email": "dup@test.com",
                "full_name": "Dup",
                "password": "Password1",
                "role": "field_worker",
            },
            headers=auth_headers(manager),
        )
        assert response.status_code == 409


class TestGetMe:
    async def test_authenticated_user_gets_profile(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        user = await make_user(db, role=UserRole.MANAGER, email="me@test.com")
        response = await client.get("/auth/me", headers=auth_headers(user))
        assert response.status_code == 200
        assert response.json()["email"] == "me@test.com"

    async def test_unauthenticated_request_returns_403(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/auth/me")
        assert response.status_code in (401, 403)
