from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.accounts.dependencies import get_current_user
from src.accounts.models import User
from src.carts.models import CartItem
from src.database.session import get_db
from src.movies.models import Movie
from src.movies.schemas import MovieResponseSchema


router = APIRouter(
    prefix="/cart",
    tags=["Cart"],
)


@router.post(
    "/{movie_id}",
    status_code=status.HTTP_201_CREATED,
)
async def add_to_cart(
    movie_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    movie_result = await db.execute(
        select(Movie).where(
            Movie.id == movie_id,
        )
    )

    movie = movie_result.scalar_one_or_none()

    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found.",
        )

    cart_item_result = await db.execute(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.movie_id == movie_id,
        )
    )

    existing_cart_item = cart_item_result.scalar_one_or_none()

    if existing_cart_item is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie is already in cart.",
        )

    cart_item = CartItem(
        user_id=current_user.id,
        movie_id=movie_id,
    )

    db.add(cart_item)
    await db.commit()

    return {
        "detail": "Movie added to cart.",
    }


@router.get(
    "",
    response_model=list[MovieResponseSchema],
)
async def get_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Movie]:
    query = (
        select(Movie)
        .join(
            CartItem,
            CartItem.movie_id == Movie.id,
        )
        .where(
            CartItem.user_id == current_user.id,
        )
        .options(
            selectinload(Movie.genre),
            selectinload(Movie.certification),
        )
        .order_by(
            CartItem.added_at.desc(),
        )
    )

    result = await db.execute(query)

    return list(result.scalars().all())


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_from_cart(
    movie_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    cart_item_result = await db.execute(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.movie_id == movie_id,
        )
    )

    cart_item = cart_item_result.scalar_one_or_none()

    if cart_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found.",
        )

    await db.execute(
        delete(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.movie_id == movie_id,
        )
    )

    await db.commit()


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def clear_cart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await db.execute(
        delete(CartItem).where(
            CartItem.user_id == current_user.id,
        )
    )

    await db.commit()
