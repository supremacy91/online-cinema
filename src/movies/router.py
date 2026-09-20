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
    summary="Get movie catalog",
    description=(
        "Return a paginated list of movies. "
        "Movies can be searched by title, filtered by genre, "
        "certification and release year, and sorted by supported fields."
    ),
    responses={
        400: {
            "description": "Invalid sorting field.",
        },
        422: {
            "description": "Invalid query parameters.",
        },
    },
)
async def get_movies(
    page: int = Query(
        default=1,
        ge=1,
        description="Page number. The first page is 1.",
        examples=[1],
    ),
    page_size: int = Query(
        default=10,
        ge=1,
        le=100,
        description=(
            "Number of movies returned per page. "
            "Allowed range: 1 to 100."
        ),
        examples=[10],
    ),
    search: str | None = Query(
        default=None,
        min_length=1,
        description=(
            "Search movies by title. "
            "The search is case-insensitive and supports partial matches."
        ),
        examples=["Matrix"],
    ),
    genre_id: int | None = Query(
        default=None,
        ge=1,
        description="Filter movies by genre ID.",
        examples=[1],
    ),
    certification_id: int | None = Query(
        default=None,
        ge=1,
        description="Filter movies by certification ID.",
        examples=[1],
    ),
    release_year: int | None = Query(
        default=None,
        ge=1888,
        description="Filter movies by release year.",
        examples=[1999],
    ),
    sort_by: str = Query(
        default="title",
        description=(
            "Field used to sort movies. "
            "Supported values: title, release_date, "
            "imdb_rating, duration_minutes."
        ),
        examples=["title"],
    ),
    order: str = Query(
        default="asc",
        pattern="^(asc|desc)$",
        description=(
            "Sorting direction. "
            "Supported values: asc or desc."
        ),
        examples=["asc"],
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
    summary="Get movie details",
    description=(
        "Return detailed information about a single movie "
        "identified by its UUID."
    ),
    responses={
        404: {
            "description": "Movie not found.",
        },
        422: {
            "description": "Invalid movie UUID.",
        },
    },
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
