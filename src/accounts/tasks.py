import asyncio

from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.accounts.email import send_email
from src.accounts.services import (
    delete_expired_activation_tokens,
)
from src.celery_app import celery_app
from src.config.settings import settings


@celery_app.task
def send_activation_email(
    email: str,
    token: str,
) -> None:
    activation_link = (
        "http://localhost:8000/accounts/activate"
        f"?token={token}"
    )

    send_email(
        recipient=email,
        subject="Activate your Online Cinema account",
        body=(
            "Welcome to Online Cinema!\n\n"
            "Use the following link to activate your account:\n"
            f"{activation_link}\n"
        ),
    )


@celery_app.task
def send_password_reset_email(
    email: str,
    token: str,
) -> None:
    reset_link = (
        "http://localhost:8000/accounts/password-reset/confirm"
        f"?token={token}"
    )

    send_email(
        recipient=email,
        subject="Reset your Online Cinema password",
        body=(
            "You requested a password reset.\n\n"
            "Use the following link to reset your password:\n"
            f"{reset_link}\n"
        ),
    )


async def _cleanup_expired_activation_tokens() -> int:
    engine = create_async_engine(
        settings.database_url,
        poolclass=NullPool,
    )

    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as db:
            return await delete_expired_activation_tokens(
                db=db,
            )
    finally:
        await engine.dispose()


@celery_app.task
def cleanup_expired_activation_tokens() -> int:
    return asyncio.run(
        _cleanup_expired_activation_tokens()
    )
