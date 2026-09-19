from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select

from src.accounts.models import ActivationToken, User
from src.accounts.security import hash_password
from src.accounts.services import (
    delete_expired_activation_tokens,
)
from src.accounts.tasks import (
    _cleanup_expired_activation_tokens,
    cleanup_expired_activation_tokens,
    send_activation_email,
    send_password_reset_email,
)


def test_send_activation_email() -> None:
    with patch(
        "src.accounts.tasks.send_email"
    ) as mocked_send_email:
        send_activation_email.run(
            "user@example.com",
            "activation-token",
        )

    mocked_send_email.assert_called_once()

    call = mocked_send_email.call_args

    assert call.kwargs["recipient"] == "user@example.com"
    assert call.kwargs["subject"] == (
        "Activate your Online Cinema account"
    )
    assert "activation-token" in call.kwargs["body"]


def test_send_password_reset_email() -> None:
    with patch(
        "src.accounts.tasks.send_email"
    ) as mocked_send_email:
        send_password_reset_email.run(
            "user@example.com",
            "reset-token",
        )

    mocked_send_email.assert_called_once()

    call = mocked_send_email.call_args

    assert call.kwargs["recipient"] == "user@example.com"
    assert call.kwargs["subject"] == (
        "Reset your Online Cinema password"
    )
    assert "reset-token" in call.kwargs["body"]


@pytest.mark.asyncio
async def test_delete_expired_activation_tokens(
    db_session,
) -> None:
    expired_user = User(
        email="expired-cleanup@example.com",
        password_hash=hash_password("Password123!"),
        is_active=False,
    )

    valid_user = User(
        email="valid-cleanup@example.com",
        password_hash=hash_password("Password123!"),
        is_active=False,
    )

    db_session.add_all(
        [
            expired_user,
            valid_user,
        ]
    )

    await db_session.flush()

    expired_token = ActivationToken(
        token="expired-cleanup-token",
        user_id=expired_user.id,
        expires_at=(
            datetime.now(timezone.utc)
            - timedelta(hours=1)
        ),
    )

    valid_token = ActivationToken(
        token="valid-cleanup-token",
        user_id=valid_user.id,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(hours=24)
        ),
    )

    db_session.add_all(
        [
            expired_token,
            valid_token,
        ]
    )

    await db_session.commit()

    deleted_count = await delete_expired_activation_tokens(
        db=db_session,
    )

    assert deleted_count == 1

    expired_result = await db_session.execute(
        select(ActivationToken).where(
            ActivationToken.token
            == "expired-cleanup-token",
        )
    )

    assert expired_result.scalar_one_or_none() is None

    valid_result = await db_session.execute(
        select(ActivationToken).where(
            ActivationToken.token
            == "valid-cleanup-token",
        )
    )

    remaining_token = valid_result.scalar_one_or_none()

    assert remaining_token is not None
    assert remaining_token.token == "valid-cleanup-token"


@pytest.mark.asyncio
async def test_cleanup_expired_activation_tokens_async() -> None:
    mocked_engine = MagicMock()
    mocked_engine.dispose = AsyncMock()

    mocked_db = MagicMock()

    session_context = AsyncMock()
    session_context.__aenter__.return_value = mocked_db

    session_factory = MagicMock(
        return_value=session_context,
    )

    with (
        patch(
            "src.accounts.tasks.create_async_engine",
            return_value=mocked_engine,
        ) as mocked_create_engine,
        patch(
            "src.accounts.tasks.async_sessionmaker",
            return_value=session_factory,
        ) as mocked_sessionmaker,
        patch(
            "src.accounts.tasks."
            "delete_expired_activation_tokens",
            new=AsyncMock(return_value=3),
        ) as mocked_delete,
    ):
        result = await _cleanup_expired_activation_tokens()

    assert result == 3

    mocked_create_engine.assert_called_once()

    mocked_sessionmaker.assert_called_once_with(
        bind=mocked_engine,
        expire_on_commit=False,
    )

    mocked_delete.assert_awaited_once_with(
        db=mocked_db,
    )

    mocked_engine.dispose.assert_awaited_once()


def test_cleanup_expired_activation_tokens_task() -> None:
    with patch(
        "src.accounts.tasks."
        "_cleanup_expired_activation_tokens",
        new=AsyncMock(return_value=2),
    ):
        result = cleanup_expired_activation_tokens.run()

    assert result == 2
