from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.base import Base


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    movies: Mapped[list["Movie"]] = relationship(
        back_populates="genre",
    )


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
    )

    movies: Mapped[list["Movie"]] = relationship(
        back_populates="certification",
    )


class Movie(Base):
    __tablename__ = "movies"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    release_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    imdb_rating: Mapped[Decimal | None] = mapped_column(
        Numeric(
            precision=3,
            scale=1,
        ),
        nullable=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(
            precision=10,
            scale=2,
        ),
        nullable=False,
        default=Decimal("0.00"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    genre_id: Mapped[int] = mapped_column(
        ForeignKey(
            "genres.id",
        ),
        nullable=False,
    )

    certification_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "certifications.id",
        ),
        nullable=True,
    )

    genre: Mapped["Genre"] = relationship(
        back_populates="movies",
    )

    certification: Mapped["Certification | None"] = relationship(
        back_populates="movies",
    )
