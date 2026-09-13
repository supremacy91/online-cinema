from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone

from src.accounts.models import ActivationToken, User
from src.accounts.schemas import (
    AccountActivationSchema,
    ActivationResendSchema,
    LoginSchema,
    TokenResponseSchema,
    UserRegisterSchema,
    UserResponseSchema,
)

from src.accounts.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from src.database.session import get_db
from src.accounts.services import (
    create_activation_token,
    recreate_activation_token,
    save_refresh_token,
)

router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"],
)


@router.post(
    "/register",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def register_user(
    data: UserRegisterSchema,
    db: AsyncSession = Depends(get_db),
) -> User:
    result = await db.execute(
        select(User).where(
            User.email == data.email,
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists.",
        )

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        is_active=False,
    )

    db.add(user)

    await db.flush()

    await create_activation_token(
        db=db,
        user=user,
    )

    await db.commit()
    await db.refresh(user)

    return user


@router.post(
    "/activate",
    status_code=status.HTTP_200_OK,
)
async def activate_account(
    data: AccountActivationSchema,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(ActivationToken).where(
            ActivationToken.token == data.token,
        )
    )
    activation_token = result.scalar_one_or_none()

    if activation_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid activation token.",
        )

    if activation_token.expires_at < datetime.now(timezone.utc):
        await db.delete(activation_token)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Activation token has expired.",
        )

    user_result = await db.execute(
        select(User).where(
            User.id == activation_token.user_id,
        )
    )
    user = user_result.scalar_one()

    user.is_active = True

    await db.delete(activation_token)
    await db.commit()

    return {
        "message": "Account activated successfully.",
    }


@router.post(
    "/activation/resend",
    status_code=status.HTTP_200_OK,
)
async def resend_activation(
    data: ActivationResendSchema,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(User).where(
            User.email == data.email,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is already active.",
        )

    await recreate_activation_token(
        db=db,
        user=user,
    )

    await db.commit()

    return {
        "message": "Activation token has been resent.",
    }


@router.post(
    "/login",
    response_model=TokenResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def login_user(
    data: LoginSchema,
    db: AsyncSession = Depends(get_db),
) -> TokenResponseSchema:
    result = await db.execute(
        select(User).where(
            User.email == data.email,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is not activated.",
        )

    access_token = create_access_token(user.id)

    refresh_token, expires_at = create_refresh_token(
        user.id,
    )

    await save_refresh_token(
        db=db,
        user=user,
        token=refresh_token,
        expires_at=expires_at,
    )

    await db.commit()

    return TokenResponseSchema(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )
