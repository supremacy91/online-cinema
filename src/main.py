from fastapi import FastAPI


app = FastAPI(
    title="Online Cinema API",
    description="API for the Online Cinema project",
    version="0.1.0",
)


@app.get(
    "/health",
    tags=["Health"],
    summary="Check application health",
)
async def health_check() -> dict[str, str]:
    return {"status": "ok"}
