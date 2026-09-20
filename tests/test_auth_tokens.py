import pytest
from sqlalchemy import select

from src.accounts.models import RefreshToken, User
from src.accounts.security import decode_token, hash_password


@pytest.mark.asyncio
async def test_login_success(
    client,
    db_session,
) -> None:
    user = User(
        email="login-success@example.com",
        password_hash=hash_password("Password123!"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()

    response = await client.post(
        "/accounts/login",
        json={
            "email": "login-success@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    access_payload = decode_token(
        data["access_token"],
    )
    refresh_payload = decode_token(
        data["refresh_token"],
    )

    assert access_payload["type"] == "access"
    assert refresh_payload["type"] == "refresh"


@pytest.mark.asyncio
async def test_login_wrong_password(
    client,
    db_session,
) -> None:
    user = User(
        email="wrong-password@example.com",
        password_hash=hash_password("Password123!"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()

    response = await client.post(
        "/accounts/login",
        json={
            "email": "wrong-password@example.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid email or password.",
    }


@pytest.mark.asyncio
async def test_login_inactive_user(
    client,
    db_session,
) -> None:
    user = User(
        email="inactive-login@example.com",
        password_hash=hash_password("Password123!"),
        is_active=False,
    )

    db_session.add(user)
    await db_session.commit()

    response = await client.post(
        "/accounts/login",
        json={
            "email": "inactive-login@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Account is not activated.",
    }


@pytest.mark.asyncio
async def test_refresh_success(
    client,
    db_session,
) -> None:
    user = User(
        email="refresh-success@example.com",
        password_hash=hash_password("Password123!"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()

    login_response = await client.post(
        "/accounts/login",
        json={
            "email": "refresh-success@example.com",
            "password": "Password123!",
        },
    )

    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]

    response = await client.post(
        "/accounts/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"

    payload = decode_token(
        data["access_token"],
    )

    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_invalid_refresh_token(
    client,
) -> None:
    response = await client.post(
        "/accounts/refresh",
        json={
            "refresh_token": "invalid-refresh-token",
        },
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Invalid refresh token.",
    }


@pytest.mark.asyncio
async def test_logout_removes_refresh_token(
    client,
    db_session,
) -> None:
    user = User(
        email="logout@example.com",
        password_hash=hash_password("Password123!"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()

    login_response = await client.post(
        "/accounts/login",
        json={
            "email": "logout@example.com",
            "password": "Password123!",
        },
    )

    assert login_response.status_code == 200

    refresh_token = login_response.json()["refresh_token"]

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token,
        )
    )

    stored_token = result.scalar_one_or_none()

    assert stored_token is not None

    logout_response = await client.post(
        "/accounts/logout",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert logout_response.status_code == 200
    assert logout_response.json() == {
        "message": "Logged out successfully.",
    }

    db_session.expire_all()

    result = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token,
        )
    )

    stored_token = result.scalar_one_or_none()

    assert stored_token is None

    refresh_response = await client.post(
        "/accounts/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert refresh_response.status_code == 401
    assert refresh_response.json() == {
        "detail": "Invalid refresh token.",
    }
