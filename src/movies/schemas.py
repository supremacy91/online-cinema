from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class GenreResponseSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


class CertificationResponseSchema(BaseModel):
    id: int
    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


class MovieCreateSchema(BaseModel):
    title: str = Field(
        min_length=1,
        max_length=255,
    )

    price: Decimal = Field(
        ge=0,
        decimal_places=2,
    )

    description: str = Field(
        min_length=1,
    )

    release_date: date

    duration_minutes: int = Field(
        gt=0,
    )

    imdb_rating: Decimal | None = Field(
        default=None,
        ge=0,
        le=10,
    )

    genre_id: int

    certification_id: int | None = None


class MovieResponseSchema(BaseModel):
    id: UUID
    title: str
    description: str
    release_date: date
    duration_minutes: int
    imdb_rating: Decimal | None
    price: Decimal
    created_at: datetime
    genre: GenreResponseSchema
    certification: CertificationResponseSchema | None

    model_config = ConfigDict(
        from_attributes=True,
    )
