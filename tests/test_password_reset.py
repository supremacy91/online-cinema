from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from src.accounts.models import PasswordResetToken, User
from src.accounts.security import hash_password, verify_password


@pytest.mark.asyncio
async def test_password_reset_request_success(
    client,
    db_session,
) -> None:
    user = User(
        email="reset-request@example.com",
        password_hash=hash_password("Password123!"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()

    response = await client.post(
        "/accounts/password-reset/request",
        json={
            "email": "reset-request@example.com",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Password reset token has been created.",
    }

    result = await db_session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
        )
    )
    reset_token = result.scalar_one_or_none()

    assert reset_token is not None


@pytest.mark.asyncio
async def test_password_reset_request_unknown_user(
    client,
) -> None:
    response = await client.post(
        "/accounts/password-reset/request",
        json={
            "email": "unknown@example.com",
        },
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "User not found.",
    }


@pytest.mark.asyncio
async def test_password_reset_confirm_success(
    client,
    db_session,
) -> None:
    user = User(
        email="reset-confirm@example.com",
        password_hash=hash_password("Password123!"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.flush()

    reset_token = PasswordResetToken(
        token="valid-reset-token",
        user_id=user.id,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(hours=1)
        ),
    )

    db_session.add(reset_token)
    await db_session.commit()

    response = await client.post(
        "/accounts/password-reset/confirm",
        json={
            "token": "valid-reset-token",
            "new_password": "NewPassword123!",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Password has been reset successfully.",
    }

    await db_session.refresh(user)

    assert verify_password(
        "NewPassword123!",
        user.password_hash,
    )

    assert not verify_password(
        "Password123!",
        user.password_hash,
    )

    result = await db_session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == "valid-reset-token",
        )
    )

    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_password_reset_invalid_token(
    client,
) -> None:
    response = await client.post(
        "/accounts/password-reset/confirm",
        json={
            "token": "invalid-reset-token",
            "new_password": "NewPassword123!",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid password reset token.",
    }


@pytest.mark.asyncio
async def test_password_reset_expired_token(
    client,
    db_session,
) -> None:
    user = User(
        email="expired-reset@example.com",
        password_hash=hash_password("Password123!"),
        is_active=True,
    )

    db_session.add(user)
    await db_session.flush()

    reset_token = PasswordResetToken(
        token="expired-reset-token",
        user_id=user.id,
        expires_at=(
            datetime.now(timezone.utc)
            - timedelta(minutes=1)
        ),
    )

    db_session.add(reset_token)
    await db_session.commit()

    response = await client.post(
        "/accounts/password-reset/confirm",
        json={
            "token": "expired-reset-token",
            "new_password": "NewPassword123!",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Password reset token has expired.",
    }

    result = await db_session.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == "expired-reset-token",
        )
    )

    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_password_reset_invalid_new_password(
    client,
) -> None:
    response = await client.post(
        "/accounts/password-reset/confirm",
        json={
            "token": "some-token",
            "new_password": "password",
        },
    )

    assert response.status_code == 422
