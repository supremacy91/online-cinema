import pytest
from httpx import AsyncClient

from src.config.settings import settings


pytestmark = pytest.mark.asyncio


async def test_docs_requires_authentication(
    client: AsyncClient,
) -> None:
    response = await client.get("/docs")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Basic"


async def test_docs_rejects_invalid_credentials(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/docs",
        auth=(
            "wrong-user",
            "wrong-password",
        ),
    )

    assert response.status_code == 401


async def test_docs_accepts_valid_credentials(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/docs",
        auth=(
            settings.docs_username,
            settings.docs_password,
        ),
    )

    assert response.status_code == 200
    assert "swagger-ui" in response.text.lower()


async def test_openapi_requires_authentication(
    client: AsyncClient,
) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 401


async def test_openapi_accepts_valid_credentials(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/openapi.json",
        auth=(
            settings.docs_username,
            settings.docs_password,
        ),
    )

    assert response.status_code == 200

    schema = response.json()

    assert schema["info"]["title"] == "Online Cinema API"
    assert "openapi" in schema
    assert "/movies" in schema["paths"]


async def test_redoc_requires_authentication(
    client: AsyncClient,
) -> None:
    response = await client.get("/redoc")

    assert response.status_code == 401


async def test_redoc_accepts_valid_credentials(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/redoc",
        auth=(
            settings.docs_username,
            settings.docs_password,
        ),
    )

    assert response.status_code == 200
    assert "redoc" in response.text.lower()
