from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.accounts.models import User
from src.accounts.schemas import (
    UserRegisterSchema,
    UserResponseSchema,
)
from src.accounts.security import hash_password
from src.database.session import get_db


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

    await db.commit()
    await db.refresh(user)

    return user
