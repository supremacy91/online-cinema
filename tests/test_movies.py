from datetime import date
from decimal import Decimal

import pytest

from src.movies.models import Certification, Genre, Movie


@pytest.mark.asyncio
async def test_get_movies_empty(
    client,
) -> None:
    response = await client.get(
        "/movies",
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_movies_success(
    client,
    db_session,
) -> None:
    genre = Genre(
        name="Sci-Fi",
    )
    certification = Certification(
        name="PG-13",
    )

    db_session.add_all(
        [
            genre,
            certification,
        ]
    )
    await db_session.flush()

    movie = Movie(
        title="Interstellar",
        description=(
            "A team travels through "
            "a wormhole in space."
        ),
        release_date=date(
            2014,
            11,
            7,
        ),
        duration_minutes=169,
        imdb_rating=Decimal("8.7"),
        genre_id=genre.id,
        certification_id=certification.id,
    )

    db_session.add(movie)
    await db_session.commit()

    response = await client.get(
        "/movies",
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["title"] == "Interstellar"
    assert data[0]["description"] == (
        "A team travels through a wormhole in space."
    )
    assert data[0]["release_date"] == "2014-11-07"
    assert data[0]["duration_minutes"] == 169
    assert data[0]["imdb_rating"] == "8.7"

    assert data[0]["genre"]["name"] == "Sci-Fi"
    assert data[0]["certification"]["name"] == "PG-13"


@pytest.mark.asyncio
async def test_get_movie_by_id(
    client,
    db_session,
) -> None:
    genre = Genre(
        name="Drama",
    )

    db_session.add(genre)
    await db_session.flush()

    movie = Movie(
        title="Forrest Gump",
        description="Drama movie.",
        release_date=date(
            1994,
            7,
            6,
        ),
        duration_minutes=142,
        imdb_rating=Decimal("8.8"),
        genre_id=genre.id,
    )

    db_session.add(movie)
    await db_session.commit()

    response = await client.get(
        f"/movies/{movie.id}",
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == str(movie.id)
    assert data["title"] == "Forrest Gump"
    assert data["genre"]["name"] == "Drama"
    assert data["certification"] is None


@pytest.mark.asyncio
async def test_get_movie_not_found(
    client,
) -> None:
    response = await client.get(
        "/movies/00000000-0000-0000-0000-000000000001",
    )

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Movie not found.",
    }


@pytest.mark.asyncio
async def test_search_movies(
    client,
    db_session,
) -> None:
    genre = Genre(
        name="Action",
    )

    db_session.add(genre)
    await db_session.flush()

    dark_knight = Movie(
        title="The Dark Knight",
        description="Batman movie.",
        release_date=date(
            2008,
            7,
            18,
        ),
        duration_minutes=152,
        imdb_rating=Decimal("9.0"),
        genre_id=genre.id,
    )

    other_movie = Movie(
        title="Gladiator",
        description="Roman movie.",
        release_date=date(
            2000,
            5,
            5,
        ),
        duration_minutes=155,
        imdb_rating=Decimal("8.5"),
        genre_id=genre.id,
    )

    db_session.add_all(
        [
            dark_knight,
            other_movie,
        ]
    )
    await db_session.commit()

    response = await client.get(
        "/movies",
        params={
            "search": "dark",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["title"] == "The Dark Knight"


@pytest.mark.asyncio
async def test_filter_movies_by_genre(
    client,
    db_session,
) -> None:
    drama = Genre(
        name="Drama",
    )
    comedy = Genre(
        name="Comedy",
    )

    db_session.add_all(
        [
            drama,
            comedy,
        ]
    )
    await db_session.flush()

    drama_movie = Movie(
        title="Drama Movie",
        description="Drama.",
        release_date=date(
            2020,
            1,
            1,
        ),
        duration_minutes=120,
        imdb_rating=Decimal("7.5"),
        genre_id=drama.id,
    )

    comedy_movie = Movie(
        title="Comedy Movie",
        description="Comedy.",
        release_date=date(
            2021,
            1,
            1,
        ),
        duration_minutes=100,
        imdb_rating=Decimal("7.0"),
        genre_id=comedy.id,
    )

    db_session.add_all(
        [
            drama_movie,
            comedy_movie,
        ]
    )
    await db_session.commit()

    response = await client.get(
        "/movies",
        params={
            "genre_id": drama.id,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["title"] == "Drama Movie"


@pytest.mark.asyncio
async def test_filter_movies_by_certification(
    client,
    db_session,
) -> None:
    genre = Genre(
        name="Sci-Fi",
    )
    pg_13 = Certification(
        name="PG-13",
    )
    r_rating = Certification(
        name="R",
    )

    db_session.add_all(
        [
            genre,
            pg_13,
            r_rating,
        ]
    )
    await db_session.flush()

    first_movie = Movie(
        title="Movie PG-13",
        description="Description.",
        release_date=date(
            2020,
            1,
            1,
        ),
        duration_minutes=100,
        imdb_rating=Decimal("7.5"),
        genre_id=genre.id,
        certification_id=pg_13.id,
    )

    second_movie = Movie(
        title="Movie R",
        description="Description.",
        release_date=date(
            2021,
            1,
            1,
        ),
        duration_minutes=110,
        imdb_rating=Decimal("8.0"),
        genre_id=genre.id,
        certification_id=r_rating.id,
    )

    db_session.add_all(
        [
            first_movie,
            second_movie,
        ]
    )
    await db_session.commit()

    response = await client.get(
        "/movies",
        params={
            "certification_id": pg_13.id,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["title"] == "Movie PG-13"


@pytest.mark.asyncio
async def test_filter_movies_by_release_year(
    client,
    db_session,
) -> None:
    genre = Genre(
        name="Drama",
    )

    db_session.add(genre)
    await db_session.flush()

    movie_2020 = Movie(
        title="Movie 2020",
        description="Description.",
        release_date=date(
            2020,
            5,
            10,
        ),
        duration_minutes=100,
        imdb_rating=Decimal("7.1"),
        genre_id=genre.id,
    )

    movie_2021 = Movie(
        title="Movie 2021",
        description="Description.",
        release_date=date(
            2021,
            5,
            10,
        ),
        duration_minutes=105,
        imdb_rating=Decimal("7.2"),
        genre_id=genre.id,
    )

    db_session.add_all(
        [
            movie_2020,
            movie_2021,
        ]
    )
    await db_session.commit()

    response = await client.get(
        "/movies",
        params={
            "release_year": 2020,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["title"] == "Movie 2020"


@pytest.mark.asyncio
async def test_sort_movies_by_imdb_rating_desc(
    client,
    db_session,
) -> None:
    genre = Genre(
        name="Drama",
    )

    db_session.add(genre)
    await db_session.flush()

    first_movie = Movie(
        title="Lower Rating",
        description="Description.",
        release_date=date(
            2020,
            1,
            1,
        ),
        duration_minutes=100,
        imdb_rating=Decimal("7.0"),
        genre_id=genre.id,
    )

    second_movie = Movie(
        title="Higher Rating",
        description="Description.",
        release_date=date(
            2020,
            1,
            2,
        ),
        duration_minutes=100,
        imdb_rating=Decimal("9.0"),
        genre_id=genre.id,
    )

    db_session.add_all(
        [
            first_movie,
            second_movie,
        ]
    )
    await db_session.commit()

    response = await client.get(
        "/movies",
        params={
            "sort_by": "imdb_rating",
            "order": "desc",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["title"] == "Higher Rating"
    assert data[1]["title"] == "Lower Rating"


@pytest.mark.asyncio
async def test_invalid_sort_field(
    client,
) -> None:
    response = await client.get(
        "/movies",
        params={
            "sort_by": "unknown",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Invalid sort field.",
    }


@pytest.mark.asyncio
async def test_movies_pagination(
    client,
    db_session,
) -> None:
    genre = Genre(
        name="Drama",
    )

    db_session.add(genre)
    await db_session.flush()

    movies = []

    for index in range(5):
        movies.append(
            Movie(
                title=f"Movie {index + 1}",
                description="Description.",
                release_date=date(
                    2020,
                    1,
                    index + 1,
                ),
                duration_minutes=100,
                imdb_rating=Decimal("7.0"),
                genre_id=genre.id,
            )
        )

    db_session.add_all(movies)
    await db_session.commit()

    response = await client.get(
        "/movies",
        params={
            "page": 2,
            "page_size": 2,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 2
    assert data[0]["title"] == "Movie 3"
    assert data[1]["title"] == "Movie 4"
