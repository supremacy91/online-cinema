from fastapi import FastAPI

from src.accounts.router import router as accounts_router
from src.carts.router import router as carts_router
from src.favorites.router import router as favorites_router
from src.movies.router import router as movies_router


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
