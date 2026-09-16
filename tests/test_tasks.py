from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select

from src.accounts.models import ActivationToken, User
from src.accounts.security import hash_password
from src.accounts.services import (
    delete_expired_activation_tokens,
)
from src.accounts.tasks import (
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
