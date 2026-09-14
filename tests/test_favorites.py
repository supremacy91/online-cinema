from datetime import date
from decimal import Decimal

import pytest

from src.accounts.models import User
from src.accounts.security import create_access_token
from src.favorites.models import Favorite
from src.movies.models import Certification, Genre, Movie


async def create_user(
    db_session,
    email: str,
) -> User:
    user = User(
        email=email,
        password_hash="test-password-hash",
        is_active=True,
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    return user


async def create_movie(
    db_session,
    title: str,
) -> Movie:
    genre = Genre(
        name=f"{title} Genre",
    )

    certification = Certification(
        name=f"{title} Certification",
    )

    db_session.add_all(
        [
            genre,
            certification,
        ]
    )

    await db_session.flush()

    movie = Movie(
        title=title,
        description="Test movie description",
        release_date=date(
            2020,
            1,
            1,
        ),
        duration_minutes=120,
        imdb_rating=Decimal("8.0"),
        genre_id=genre.id,
        certification_id=certification.id,
    )

    db_session.add(movie)
    await db_session.commit()
    await db_session.refresh(movie)

    return movie


def get_auth_headers(
    user: User,
) -> dict[str, str]:
    token = create_access_token(
        user.id,
    )

    return {
        "Authorization": f"Bearer {token}",
    }


@pytest.mark.asyncio
async def test_add_favorite_success(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "favorite@example.com",
    )

    movie = await create_movie(
        db_session,
        "Interstellar",
    )

    response = await client.post(
        f"/favorites/{movie.id}",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 201
    assert response.json() == {
        "detail": "Movie added to favorites.",
    }


@pytest.mark.asyncio
async def test_add_duplicate_favorite(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "duplicate@example.com",
    )

    movie = await create_movie(
        db_session,
        "The Matrix",
    )

    favorite = Favorite(
        user_id=user.id,
        movie_id=movie.id,
    )

    db_session.add(favorite)
    await db_session.commit()

    response = await client.post(
        f"/favorites/{movie.id}",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Movie is already in favorites."
    )


@pytest.mark.asyncio
async def test_add_nonexistent_movie_to_favorites(
    client,
    db_session,
) -> None:
    from uuid import uuid4

    user = await create_user(
        db_session,
        "missing@example.com",
    )

    response = await client.post(
        f"/favorites/{uuid4()}",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found."


@pytest.mark.asyncio
async def test_get_favorites_empty(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "empty@example.com",
    )

    response = await client.get(
        "/favorites",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_favorites_success(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "list@example.com",
    )

    movie = await create_movie(
        db_session,
        "Inception",
    )

    favorite = Favorite(
        user_id=user.id,
        movie_id=movie.id,
    )

    db_session.add(favorite)
    await db_session.commit()

    response = await client.get(
        "/favorites",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(movie.id)
    assert data[0]["title"] == "Inception"


@pytest.mark.asyncio
async def test_get_favorites_returns_only_current_user_movies(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "owner@example.com",
    )

    other_user = await create_user(
        db_session,
        "other@example.com",
    )

    own_movie = await create_movie(
        db_session,
        "Own Movie",
    )

    other_movie = await create_movie(
        db_session,
        "Other Movie",
    )

    db_session.add_all(
        [
            Favorite(
                user_id=user.id,
                movie_id=own_movie.id,
            ),
            Favorite(
                user_id=other_user.id,
                movie_id=other_movie.id,
            ),
        ]
    )

    await db_session.commit()

    response = await client.get(
        "/favorites",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(own_movie.id)
    assert data[0]["title"] == "Own Movie"


@pytest.mark.asyncio
async def test_remove_favorite_success(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "remove@example.com",
    )

    movie = await create_movie(
        db_session,
        "Remove Movie",
    )

    favorite = Favorite(
        user_id=user.id,
        movie_id=movie.id,
    )

    db_session.add(favorite)
    await db_session.commit()

    response = await client.delete(
        f"/favorites/{movie.id}",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_remove_nonexistent_favorite(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "remove-missing@example.com",
    )

    movie = await create_movie(
        db_session,
        "Not Favorite",
    )

    response = await client.delete(
        f"/favorites/{movie.id}",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Favorite not found."


@pytest.mark.asyncio
async def test_favorites_require_authentication(
    client,
) -> None:
    response = await client.get(
        "/favorites",
    )

    assert response.status_code in {
        401,
        403,
    }
