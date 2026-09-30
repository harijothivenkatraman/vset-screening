from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.infrastructure.persistence.database import init_db
from app.presentation.routers import (
    actions_router,
    companies_router,
    import_router,
    sections_router,
    sources_router,
)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Initialize DB schema
    await init_db()
    yield


app = FastAPI(
    title="vSET Startup Screening API",
    description="Backend API for the vSET Startup Screening Dashboard presenting structured company assessment reports.",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/api/v1/openapi.json",
)

# CORS middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal Server Error",
            "statusCode": 500,
            "message": str(exc),
        },
    )


# Health check
@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    return {"status": "ok", "environment": settings.ENVIRONMENT}


# API v1 router aggregation
api_v1_prefix = "/api/v1"
app.include_router(companies_router, prefix=api_v1_prefix)
app.include_router(sections_router, prefix=api_v1_prefix)
app.include_router(actions_router, prefix=api_v1_prefix)
app.include_router(sources_router, prefix=api_v1_prefix)
app.include_router(import_router, prefix=api_v1_prefix)
