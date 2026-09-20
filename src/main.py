import secrets

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.openapi.docs import (
    get_redoc_html,
    get_swagger_ui_html,
)
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from src.accounts.router import router as accounts_router
from src.carts.router import router as carts_router
from src.config.settings import settings
from src.favorites.router import router as favorites_router
from src.movies.router import router as movies_router


docs_security = HTTPBasic()


def verify_docs_credentials(
    credentials: HTTPBasicCredentials = Depends(
        docs_security,
    ),
) -> None:
    username_is_correct = secrets.compare_digest(
        credentials.username,
        settings.docs_username,
    )
    password_is_correct = secrets.compare_digest(
        credentials.password,
        settings.docs_password,
    )

    if not (
        username_is_correct
        and password_is_correct
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid documentation credentials.",
            headers={
                "WWW-Authenticate": "Basic",
            },
        )


tags_metadata = [
    {
        "name": "Accounts",
        "description": (
            "User registration, account activation, authentication, "
            "JWT token management, logout, and password reset."
        ),
    },
    {
        "name": "Movies",
        "description": (
            "Browse the movie catalog, search for movies, "
            "filter results, sort results, and retrieve movie details."
        ),
    },
    {
        "name": "Favorites",
        "description": (
            "Manage the authenticated user's favorite movies."
        ),
    },
    {
        "name": "Cart",
        "description": (
            "Manage movies in the authenticated user's shopping cart."
        ),
    },
    {
        "name": "Health",
        "description": (
            "Application health check endpoint."
        ),
    },
]


app = FastAPI(
    title="Online Cinema API",
    description=(
        "REST API for an online cinema service.\n\n"
        "The API provides account registration and activation, "
        "JWT authentication, password reset, movie catalog browsing, "
        "favorites management, and shopping cart management.\n\n"
        "Background tasks such as email delivery and expired activation "
        "token cleanup are processed asynchronously with Celery and Redis."
    ),
    version="1.0.0",
    openapi_tags=tags_metadata,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


app.include_router(accounts_router)
app.include_router(movies_router)
app.include_router(favorites_router)
app.include_router(carts_router)


@app.get(
    "/health",
    tags=["Health"],
    summary="Check application health",
    description=(
        "Check whether the Online Cinema API is running "
        "and able to respond to requests."
    ),
)
async def health_check() -> dict[str, str]:
    return {
        "status": "ok",
    }


@app.get(
    "/openapi.json",
    include_in_schema=False,
)
async def protected_openapi(
    _: None = Depends(verify_docs_credentials),
) -> JSONResponse:
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
        tags=app.openapi_tags,
    )

    return JSONResponse(schema)


@app.get(
    "/docs",
    include_in_schema=False,
)
async def protected_swagger_ui(
    _: None = Depends(verify_docs_credentials),
) -> HTMLResponse:
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - Swagger UI",
    )


@app.get(
    "/redoc",
    include_in_schema=False,
)
async def protected_redoc(
    _: None = Depends(verify_docs_credentials),
) -> HTMLResponse:
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=f"{app.title} - ReDoc",
    )
