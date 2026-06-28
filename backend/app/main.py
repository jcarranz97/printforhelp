"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.activity.router import activity_router, comments_router
from app.auth.router import router as auth_router
from app.bootstrap import run_startup_bootstrap
from app.collection_centers.router import router as collection_centers_router
from app.config import settings
from app.contributions.router import router as contributions_router
from app.exceptions import (
    AppExceptionError,
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.organizations.router import router as organizations_router
from app.parts.router import router as parts_router
from app.requests.router import router as requests_router
from app.shipments.router import router as shipments_router
from app.users.router import router as users_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Bootstrap the default admin (and dev seed data) on startup."""
    run_startup_bootstrap()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.VERSION,
        description="Coordination platform for community 3D-printed aid",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_exception_handler(AppExceptionError, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(organizations_router, prefix="/api/v1")
    app.include_router(collection_centers_router, prefix="/api/v1")
    app.include_router(parts_router, prefix="/api/v1")
    app.include_router(requests_router, prefix="/api/v1")
    app.include_router(contributions_router, prefix="/api/v1")
    app.include_router(shipments_router, prefix="/api/v1")
    app.include_router(activity_router, prefix="/api/v1")
    app.include_router(comments_router, prefix="/api/v1")

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint providing basic app info."""
        return {
            "message": f"{settings.APP_NAME} is running",
            "version": settings.VERSION,
        }

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "printforhelp-api",
            "version": settings.VERSION,
        }

    return app


app = create_app()
