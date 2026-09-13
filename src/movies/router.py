from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.session import get_db
from src.movies.models import Movie
from src.movies.schemas import MovieResponseSchema


router = APIRouter(
    prefix="/movies",
    tags=["Movies"],
)


@router.get(
    "",
    response_model=list[MovieResponseSchema],
)
async def get_movies(
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
    ),
    genre_id: int | None = Query(
        default=None,
        ge=1,
    ),
    certification_id: int | None = Query(
        default=None,
        ge=1,
    ),
    release_year: int | None = Query(
        default=None,
        ge=1888,
    ),
    sort_by: str = Query(
        default="title",
    ),
    order: str = Query(
        default="asc",
        pattern="^(asc|desc)$",
    ),
    db: AsyncSession = Depends(get_db),
) -> list[Movie]:
    query = select(Movie).options(
        selectinload(Movie.genre),
        selectinload(Movie.certification),
    )

    if search is not None:
        query = query.where(
            Movie.title.ilike(
                f"%{search}%"
            )
        )

    if genre_id is not None:
        query = query.where(
            Movie.genre_id == genre_id
        )

    if certification_id is not None:
        query = query.where(
            Movie.certification_id
            == certification_id
        )

    if release_year is not None:
        query = query.where(
            Movie.release_date.between(
                date(
                    release_year,
                    1,
                    1,
                ),
                date(
                    release_year,
                    12,
                    31,
                ),
            )
        )

    sort_fields = {
        "title": Movie.title,
        "release_date": Movie.release_date,
        "imdb_rating": Movie.imdb_rating,
        "duration_minutes": Movie.duration_minutes,
    }

    sort_column = sort_fields.get(
        sort_by
    )

    if sort_column is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid sort field.",
        )

    if order == "desc":
        query = query.order_by(
            desc(sort_column)
        )
    else:
        query = query.order_by(
            asc(sort_column)
        )

    offset = (page - 1) * page_size

    query = (
        query
        .offset(offset)
        .limit(page_size)
    )

    result = await db.execute(query)

    return list(
        result.scalars().all()
    )


@router.get(
    "/{movie_id}",
    response_model=MovieResponseSchema,
)
async def get_movie(
    movie_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Movie:
    query = (
        select(Movie)
        .options(
            selectinload(Movie.genre),
            selectinload(Movie.certification),
        )
        .where(
            Movie.id == movie_id
        )
    )

    result = await db.execute(query)
    movie = result.scalar_one_or_none()

    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Movie not found.",
        )

    return movie
