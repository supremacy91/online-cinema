from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from src.accounts.models import (
    ActivationToken,
    PasswordResetToken,
    RefreshToken,
    User,
)


ACTIVATION_TOKEN_LIFETIME_HOURS = 24
PASSWORD_RESET_TOKEN_LIFETIME_HOURS = 1


async def create_password_reset_token(
    db: AsyncSession,
    user: User,
) -> PasswordResetToken:
    await db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id,
        )
    )

    token = PasswordResetToken(
        token=token_urlsafe(32),
        user_id=user.id,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(
                hours=PASSWORD_RESET_TOKEN_LIFETIME_HOURS,
            )
        ),
    )

    db.add(token)
    await db.flush()

    return token


async def create_activation_token(
    db: AsyncSession,
    user: User,
) -> ActivationToken:
    token = ActivationToken(
        token=token_urlsafe(32),
        user_id=user.id,
        expires_at=(
            datetime.now(timezone.utc)
            + timedelta(hours=ACTIVATION_TOKEN_LIFETIME_HOURS)
        ),
    )

    db.add(token)
    await db.flush()

    return token


async def recreate_activation_token(
    db: AsyncSession,
    user: User,
) -> ActivationToken:
    await db.execute(
        delete(ActivationToken).where(
            ActivationToken.user_id == user.id,
        )
    )

    return await create_activation_token(
        db=db,
        user=user,
    )


async def save_refresh_token(
    db: AsyncSession,
    user: User,
    token: str,
    expires_at: datetime,
) -> RefreshToken:
    refresh_token = RefreshToken(
        token=token,
        user_id=user.id,
        expires_at=expires_at,
    )

    db.add(refresh_token)
    await db.flush()

    return refresh_token
