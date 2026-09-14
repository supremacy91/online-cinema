from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.accounts.dependencies import get_current_user
from src.accounts.models import User
from src.database.session import get_db
from src.favorites.models import Favorite
from src.movies.models import Movie
from src.movies.schemas import MovieResponseSchema


router = APIRouter(
    prefix="/favorites",
    tags=["Favorites"],
)


@router.post(
    "/{movie_id}",
    status_code=status.HTTP_201_CREATED,
)
async def add_favorite(
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

    favorite_result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.movie_id == movie_id,
        )
    )

    existing_favorite = favorite_result.scalar_one_or_none()

    if existing_favorite is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Movie is already in favorites.",
        )

    favorite = Favorite(
        user_id=current_user.id,
        movie_id=movie_id,
    )

    db.add(favorite)
    await db.commit()

    return {
        "detail": "Movie added to favorites.",
    }


@router.get(
    "",
    response_model=list[MovieResponseSchema],
)
async def get_favorites(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Movie]:
    query = (
        select(Movie)
        .join(
            Favorite,
            Favorite.movie_id == Movie.id,
        )
        .where(
            Favorite.user_id == current_user.id,
        )
        .options(
            selectinload(Movie.genre),
            selectinload(Movie.certification),
        )
        .order_by(
            Favorite.created_at.desc(),
        )
    )

    result = await db.execute(query)

    return list(result.scalars().all())


@router.delete(
    "/{movie_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_favorite(
    movie_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    favorite_result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.movie_id == movie_id,
        )
    )

    favorite = favorite_result.scalar_one_or_none()

    if favorite is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favorite not found.",
        )

    await db.execute(
        delete(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.movie_id == movie_id,
        )
    )

    await db.commit()
