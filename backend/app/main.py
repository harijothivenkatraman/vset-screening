"""Main FastAPI application for Founder Profiles standalone app."""
from contextlib import asynccontextmanager
import logging
import sys
from typing import AsyncGenerator

from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import get_settings
from app.infrastructure.persistence.database import engine, init_db
from app.presentation.routers import founders_router

# Standard logging configuration to stdout (never logging credentials, secrets or payloads)
logging.basicConfig(
    level=logging.INFO,
    stream=sys.stdout,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vset.founder_profiles")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize DB schema
    await init_db()
    yield


app = FastAPI(
    title="Founder Profiles API",
    description="Standalone Backend API for Founder Profiles management, public profile extraction, text/PDF evidence ingestion, and canonical export.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
)

# CORS middleware configuration (honors parsed CORS_ORIGINS from settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled server exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "statusCode": 500,
            "message": str(exc),
        },
    )


# Health check: executes SELECT 1 to verify database reachability
@app.get("/health", tags=["system"])
async def health_check(response: Response) -> dict[str, str]:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "environment": settings.ENVIRONMENT}
    except Exception as exc:
        logger.warning("Database health check failed: %s", exc)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unhealthy", "environment": settings.ENVIRONMENT}


# Mount standalone Founder Profiles router
app.include_router(founders_router, prefix="/api/v1")
