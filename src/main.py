from fastapi import FastAPI

from src.accounts.router import router as accounts_router
from src.favorites.router import router as favorites_router
from src.movies.router import router as movies_router
from src.carts.router import router as carts_router

app = FastAPI(
    title="Online Cinema API",
    description="API for the Online Cinema project",
    version="0.1.0",
)

app.include_router(accounts_router)
app.include_router(movies_router)
app.include_router(favorites_router)
app.include_router(carts_router)


@app.get(
    "/health",
    tags=["Health"],
    summary="Check application health",
)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
