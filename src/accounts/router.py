from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import (
    ActivationToken,
    PasswordResetToken,
    RefreshToken,
    User,
)
from src.accounts.schemas import (
    AccessTokenResponseSchema,
    AccountActivationSchema,
    ActivationResendSchema,
    LoginSchema,
    PasswordResetConfirmSchema,
    PasswordResetRequestSchema,
    RefreshTokenSchema,
    TokenResponseSchema,
    UserRegisterSchema,
    UserResponseSchema,
)
from src.accounts.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from src.accounts.services import (
    create_activation_token,
    create_password_reset_token,
    recreate_activation_token,
    save_refresh_token,
)
from src.accounts.tasks import (
    send_activation_email,
    send_password_reset_email,
)
from src.database.session import get_db


router = APIRouter(
    prefix="/accounts",
    tags=["Accounts"],
)


@router.post(
    "/register",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description=(
        "Create a new inactive user account. "
        "An activation token valid for 24 hours is generated "
        "and an activation email is queued for asynchronous delivery."
    ),
    responses={
        409: {
            "description": "A user with this email already exists.",
        },
        422: {
            "description": "Invalid registration data.",
        },
    },
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

    activation_token = await create_activation_token(
        db=db,
        user=user,
    )

    await db.commit()
    await db.refresh(user)

    send_activation_email.delay(
        user.email,
        activation_token.token,
    )

    return user


@router.post(
    "/activate",
    status_code=status.HTTP_200_OK,
    summary="Activate a user account",
    description=(
        "Activate a previously registered account using "
        "the activation token sent by email. "
        "The token is deleted after successful activation."
    ),
    responses={
        400: {
            "description": "The activation token is invalid or expired.",
        },
        422: {
            "description": "Invalid request data.",
        },
    },
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
    summary="Resend an account activation email",
    description=(
        "Generate a new activation token for an inactive account. "
        "Any previous activation token for the user is replaced. "
        "The new token is valid for 24 hours and the activation email "
        "is queued for asynchronous delivery."
    ),
    responses={
        400: {
            "description": "The account is already active.",
        },
        404: {
            "description": "User not found.",
        },
        422: {
            "description": "Invalid request data.",
        },
    },
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

    activation_token = await recreate_activation_token(
        db=db,
        user=user,
    )

    await db.commit()

    send_activation_email.delay(
        user.email,
        activation_token.token,
    )

    return {
        "message": "Activation token has been resent.",
    }


@router.post(
    "/login",
    response_model=TokenResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Log in to an account",
    description=(
        "Authenticate an active user using email and password. "
        "Returns a short-lived access token and a refresh token. "
        "The refresh token is stored in the database."
    ),
    responses={
        401: {
            "description": "Invalid email or password.",
        },
        403: {
            "description": "The account has not been activated.",
        },
        422: {
            "description": "Invalid login data.",
        },
    },
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


@router.post(
    "/refresh",
    response_model=AccessTokenResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Refresh an access token",
    description=(
        "Issue a new access token using a valid refresh token. "
        "The refresh token must exist in the database, must not "
        "be expired, and must contain a valid JWT refresh payload."
    ),
    responses={
        401: {
            "description": "The refresh token is invalid or expired.",
        },
        422: {
            "description": "Invalid request data.",
        },
    },
)
async def refresh_access_token(
    data: RefreshTokenSchema,
    db: AsyncSession = Depends(get_db),
) -> AccessTokenResponseSchema:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == data.refresh_token,
        )
    )
    stored_token = result.scalar_one_or_none()

    if stored_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    if stored_token.expires_at < datetime.now(timezone.utc):
        await db.delete(stored_token)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired.",
        )

    try:
        payload = decode_token(data.refresh_token)
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    user_result = await db.execute(
        select(User).where(
            User.id == user_id,
        )
    )
    user = user_result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    access_token = create_access_token(user.id)

    return AccessTokenResponseSchema(
        access_token=access_token,
        token_type="bearer",
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Log out of an account",
    description=(
        "Invalidate the supplied refresh token by deleting it "
        "from the database. The token can no longer be used "
        "to obtain new access tokens."
    ),
    responses={
        401: {
            "description": "Invalid refresh token.",
        },
        422: {
            "description": "Invalid request data.",
        },
    },
)
async def logout_user(
    data: RefreshTokenSchema,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == data.refresh_token,
        )
    )
    stored_token = result.scalar_one_or_none()

    if stored_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token.",
        )

    await db.delete(stored_token)
    await db.commit()

    return {
        "message": "Logged out successfully.",
    }


@router.post(
    "/password-reset/request",
    status_code=status.HTTP_200_OK,
    summary="Request a password reset",
    description=(
        "Create a password reset token for an existing user. "
        "Any previous reset token is replaced and a password reset "
        "email is queued for asynchronous delivery."
    ),
    responses={
        404: {
            "description": "User not found.",
        },
        422: {
            "description": "Invalid request data.",
        },
    },
)
async def request_password_reset(
    data: PasswordResetRequestSchema,
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

    reset_token = await create_password_reset_token(
        db=db,
        user=user,
    )

    await db.commit()

    send_password_reset_email.delay(
        user.email,
        reset_token.token,
    )

    return {
        "message": "Password reset token has been created.",
    }


@router.post(
    "/password-reset/confirm",
    status_code=status.HTTP_200_OK,
    summary="Confirm a password reset",
    description=(
        "Set a new password using a valid password reset token. "
        "The new password must satisfy the password complexity rules. "
        "The reset token is deleted after the password is changed."
    ),
    responses={
        400: {
            "description": "The password reset token is invalid or expired.",
        },
        422: {
            "description": "The new password or request data is invalid.",
        },
    },
)
async def confirm_password_reset(
    data: PasswordResetConfirmSchema,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == data.token,
        )
    )
    reset_token = result.scalar_one_or_none()

    if reset_token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password reset token.",
        )

    if reset_token.expires_at < datetime.now(timezone.utc):
        await db.delete(reset_token)
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired.",
        )

    user_result = await db.execute(
        select(User).where(
            User.id == reset_token.user_id,
        )
    )
    user = user_result.scalar_one()

    user.password_hash = hash_password(
        data.new_password,
    )

    await db.delete(reset_token)
    await db.commit()

    return {
        "message": "Password has been reset successfully.",
    }
