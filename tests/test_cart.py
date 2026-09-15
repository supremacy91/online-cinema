from datetime import date
from decimal import Decimal

import pytest

from src.accounts.models import User
from src.accounts.security import create_access_token
from src.carts.models import CartItem
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
        price=Decimal("9.99"),
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
async def test_add_to_cart_success(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "cart@example.com",
    )

    movie = await create_movie(
        db_session,
        "Interstellar",
    )

    response = await client.post(
        f"/cart/{movie.id}",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 201
    assert response.json() == {
        "detail": "Movie added to cart.",
    }


@pytest.mark.asyncio
async def test_add_duplicate_to_cart(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "duplicate-cart@example.com",
    )

    movie = await create_movie(
        db_session,
        "The Matrix",
    )

    cart_item = CartItem(
        user_id=user.id,
        movie_id=movie.id,
    )

    db_session.add(cart_item)
    await db_session.commit()

    response = await client.post(
        f"/cart/{movie.id}",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Movie is already in cart."
    )


@pytest.mark.asyncio
async def test_add_nonexistent_movie_to_cart(
    client,
    db_session,
) -> None:
    from uuid import uuid4

    user = await create_user(
        db_session,
        "missing-cart@example.com",
    )

    response = await client.post(
        f"/cart/{uuid4()}",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Movie not found."


@pytest.mark.asyncio
async def test_get_cart_empty(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "empty-cart@example.com",
    )

    response = await client.get(
        "/cart",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_cart_success(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "cart-list@example.com",
    )

    movie = await create_movie(
        db_session,
        "Inception",
    )

    db_session.add(
        CartItem(
            user_id=user.id,
            movie_id=movie.id,
        )
    )

    await db_session.commit()

    response = await client.get(
        "/cart",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(movie.id)
    assert data[0]["title"] == "Inception"
    assert Decimal(data[0]["price"]) == Decimal("9.99")


@pytest.mark.asyncio
async def test_get_cart_returns_only_current_user_movies(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "cart-owner@example.com",
    )

    other_user = await create_user(
        db_session,
        "other-cart@example.com",
    )

    own_movie = await create_movie(
        db_session,
        "Own Cart Movie",
    )

    other_movie = await create_movie(
        db_session,
        "Other Cart Movie",
    )

    db_session.add_all(
        [
            CartItem(
                user_id=user.id,
                movie_id=own_movie.id,
            ),
            CartItem(
                user_id=other_user.id,
                movie_id=other_movie.id,
            ),
        ]
    )

    await db_session.commit()

    response = await client.get(
        "/cart",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(own_movie.id)


@pytest.mark.asyncio
async def test_remove_from_cart_success(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "remove-cart@example.com",
    )

    movie = await create_movie(
        db_session,
        "Remove Cart Movie",
    )

    db_session.add(
        CartItem(
            user_id=user.id,
            movie_id=movie.id,
        )
    )

    await db_session.commit()

    response = await client.delete(
        f"/cart/{movie.id}",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_remove_nonexistent_cart_item(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "remove-missing-cart@example.com",
    )

    movie = await create_movie(
        db_session,
        "Not In Cart",
    )

    response = await client.delete(
        f"/cart/{movie.id}",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Cart item not found."
    )


@pytest.mark.asyncio
async def test_clear_cart(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "clear-cart@example.com",
    )

    movie_1 = await create_movie(
        db_session,
        "Cart Movie One",
    )

    movie_2 = await create_movie(
        db_session,
        "Cart Movie Two",
    )

    db_session.add_all(
        [
            CartItem(
                user_id=user.id,
                movie_id=movie_1.id,
            ),
            CartItem(
                user_id=user.id,
                movie_id=movie_2.id,
            ),
        ]
    )

    await db_session.commit()

    response = await client.delete(
        "/cart",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 204

    response = await client.get(
        "/cart",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_clear_cart_does_not_clear_other_user_cart(
    client,
    db_session,
) -> None:
    user = await create_user(
        db_session,
        "clear-owner@example.com",
    )

    other_user = await create_user(
        db_session,
        "clear-other@example.com",
    )

    own_movie = await create_movie(
        db_session,
        "Clear Own Movie",
    )

    other_movie = await create_movie(
        db_session,
        "Keep Other Movie",
    )

    db_session.add_all(
        [
            CartItem(
                user_id=user.id,
                movie_id=own_movie.id,
            ),
            CartItem(
                user_id=other_user.id,
                movie_id=other_movie.id,
            ),
        ]
    )

    await db_session.commit()

    response = await client.delete(
        "/cart",
        headers=get_auth_headers(user),
    )

    assert response.status_code == 204

    response = await client.get(
        "/cart",
        headers=get_auth_headers(other_user),
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["id"] == str(other_movie.id)


@pytest.mark.asyncio
async def test_cart_requires_authentication(
    client,
) -> None:
    response = await client.get(
        "/cart",
    )

    assert response.status_code in {
        401,
        403,
    }
