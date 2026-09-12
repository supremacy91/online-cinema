from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import ActivationToken, User


ACTIVATION_TOKEN_LIFETIME_HOURS = 24


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
