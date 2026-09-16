from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from src.accounts.models import ActivationToken, User


@pytest.mark.asyncio
async def test_register_success(
    client,
    db_session,
) -> None:
    with patch(
        "src.accounts.router.send_activation_email.delay"
    ) as mocked_email:
        response = await client.post(
            "/accounts/register",
            json={
                "email": "user@example.com",
                "password": "Password123!",
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["email"] == "user@example.com"
    assert data["is_active"] is False
    assert "id" in data

    result = await db_session.execute(
        select(User).where(
            User.email == "user@example.com",
        )
    )
    user = result.scalar_one()

    assert user.password_hash != "Password123!"
    assert user.is_active is False

    token_result = await db_session.execute(
        select(ActivationToken).where(
            ActivationToken.user_id == user.id,
        )
    )
    activation_token = token_result.scalar_one()

    assert activation_token.token
    assert activation_token.expires_at > datetime.now(
        timezone.utc
    )

    mocked_email.assert_called_once()

    call = mocked_email.call_args

    assert call.args[0] == "user@example.com"
    assert call.args[1] == activation_token.token


@pytest.mark.asyncio
async def test_register_duplicate_email(
    client,
) -> None:
    user_data = {
        "email": "duplicate@example.com",
        "password": "Password123!",
    }

    first_response = await client.post(
        "/accounts/register",
        json=user_data,
    )

    second_response = await client.post(
        "/accounts/register",
        json=user_data,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "User with this email already exists."
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "password",
    [
        "short",
        "password123!",
        "PASSWORD123!",
        "Password!",
        "Password123",
    ],
)
async def test_register_invalid_password(
    client,
    password: str,
) -> None:
    response = await client.post(
        "/accounts/register",
        json={
            "email": "invalid@example.com",
            "password": password,
        },
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_activate_success(
    client,
    db_session,
) -> None:
    await client.post(
        "/accounts/register",
        json={
            "email": "activate@example.com",
            "password": "Password123!",
        },
    )

    result = await db_session.execute(
        select(User).where(
            User.email == "activate@example.com",
        )
    )
    user = result.scalar_one()

    token_result = await db_session.execute(
        select(ActivationToken).where(
            ActivationToken.user_id == user.id,
        )
    )
    activation_token = token_result.scalar_one()

    response = await client.post(
        "/accounts/activate",
        json={
            "token": activation_token.token,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Account activated successfully.",
    }

    await db_session.refresh(user)

    assert user.is_active is True

    remaining_token = await db_session.execute(
        select(ActivationToken).where(
            ActivationToken.user_id == user.id,
        )
    )

    assert remaining_token.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_activate_invalid_token(
    client,
) -> None:
    response = await client.post(
        "/accounts/activate",
        json={
            "token": "invalid-token",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Invalid activation token."
    )


@pytest.mark.asyncio
async def test_activate_expired_token(
    client,
    db_session,
) -> None:
    await client.post(
        "/accounts/register",
        json={
            "email": "expired@example.com",
            "password": "Password123!",
        },
    )

    user_result = await db_session.execute(
        select(User).where(
            User.email == "expired@example.com",
        )
    )
    user = user_result.scalar_one()

    token_result = await db_session.execute(
        select(ActivationToken).where(
            ActivationToken.user_id == user.id,
        )
    )
    activation_token = token_result.scalar_one()

    activation_token.expires_at = (
        datetime.now(timezone.utc)
        - timedelta(hours=1)
    )

    await db_session.commit()

    response = await client.post(
        "/accounts/activate",
        json={
            "token": activation_token.token,
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Activation token has expired."
    )

    token_result = await db_session.execute(
        select(ActivationToken).where(
            ActivationToken.user_id == user.id,
        )
    )

    assert token_result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_resend_activation_success(
    client,
    db_session,
) -> None:
    await client.post(
        "/accounts/register",
        json={
            "email": "resend@example.com",
            "password": "Password123!",
        },
    )

    user_result = await db_session.execute(
        select(User).where(
            User.email == "resend@example.com",
        )
    )
    user = user_result.scalar_one()
    user_id = user.id

    token_result = await db_session.execute(
        select(ActivationToken).where(
            ActivationToken.user_id == user_id,
        )
    )
    old_token = token_result.scalar_one().token

    with patch(
        "src.accounts.router.send_activation_email.delay"
    ) as mocked_email:
        response = await client.post(
            "/accounts/activation/resend",
            json={
                "email": "resend@example.com",
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Activation token has been resent.",
    }

    db_session.expire_all()

    token_result = await db_session.execute(
        select(ActivationToken).where(
            ActivationToken.user_id == user_id,
        )
    )
    new_token = token_result.scalar_one()

    assert new_token.token != old_token
    assert new_token.expires_at > datetime.now(
        timezone.utc
    )

    mocked_email.assert_called_once()

    call = mocked_email.call_args

    assert call.args[0] == "resend@example.com"
    assert call.args[1] == new_token.token


@pytest.mark.asyncio
async def test_resend_for_active_user(
    client,
    db_session,
) -> None:
    await client.post(
        "/accounts/register",
        json={
            "email": "active@example.com",
            "password": "Password123!",
        },
    )

    user_result = await db_session.execute(
        select(User).where(
            User.email == "active@example.com",
        )
    )
    user = user_result.scalar_one()

    token_result = await db_session.execute(
        select(ActivationToken).where(
            ActivationToken.user_id == user.id,
        )
    )
    activation_token = token_result.scalar_one()

    await client.post(
        "/accounts/activate",
        json={
            "token": activation_token.token,
        },
    )

    response = await client.post(
        "/accounts/activation/resend",
        json={
            "email": "active@example.com",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Account is already active."
    )


@pytest.mark.asyncio
async def test_resend_for_unknown_user(
    client,
) -> None:
    response = await client.post(
        "/accounts/activation/resend",
        json={
            "email": "unknown@example.com",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found."
