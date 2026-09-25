from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

from app.database import create_pool, close_pool
from app.routers import travel_plans, locations


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_pool()
    yield
    await close_pool()


app = FastAPI(
    title="Traveler API",
    description="API для планування подорожей",
    lifespan=lifespan
)

# Підключення маршрутів
app.include_router(travel_plans.router)
app.include_router(locations.router)


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={
            "detail": jsonable_encoder(exc.errors()),
            "error": "Validation error"
        }
    )


# Health Check для k6
@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "database": "connected"
    }