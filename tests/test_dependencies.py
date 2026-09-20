from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.accounts.dependencies import get_current_user
from src.accounts.models import User
from src.config.settings import settings


def create_test_token(
    user_id: str,
    token_type: str = "access",
) -> str:
    now = datetime.now(timezone.utc)

    payload = {
        "sub": user_id,
        "type": token_type,
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }

    return jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )


@pytest.mark.asyncio
async def test_get_current_user_success(
    db_session,
) -> None:
    user = User(
        email="current@example.com",
        password_hash="test-password-hash",
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_test_token(
        user_id=str(user.id),
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    current_user = await get_current_user(
        credentials=credentials,
        db=db_session,
    )

    assert current_user.id == user.id
    assert current_user.email == user.email
    assert current_user.is_active is True


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(
    db_session,
) -> None:
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="invalid-token",
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(
            credentials=credentials,
            db=db_session,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid access token."


@pytest.mark.asyncio
async def test_get_current_user_rejects_refresh_token(
    db_session,
) -> None:
    user = User(
        email="refresh@example.com",
        password_hash="test-password-hash",
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_test_token(
        user_id=str(user.id),
        token_type="refresh",
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(
            credentials=credentials,
            db=db_session,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid access token."


@pytest.mark.asyncio
async def test_get_current_user_rejects_inactive_user(
    db_session,
) -> None:
    user = User(
        email="inactive@example.com",
        password_hash="test-password-hash",
        is_active=False,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_test_token(
        user_id=str(user.id),
    )

    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials=token,
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(
            credentials=credentials,
            db=db_session,
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid access token."
