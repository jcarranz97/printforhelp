"""FastAPI application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
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
    ratelimit_exception_handler,
    validation_exception_handler,
)
from app.notices.router import router as notices_router
from app.notifications.router import router as notifications_router, watches_router
from app.organizations.router import router as organizations_router
from app.ratelimit import limiter
from app.requests.router import router as requests_router
from app.resources.router import router as resources_router
from app.scheduled.runner import EmailOutboxWorker
from app.shipments.router import router as shipments_router
from app.tracking.router import public_router as track_public_router, tracking_router
from app.uploads.router import router as uploads_router
from app.users.router import router as users_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Bootstrap the default admin and start the email drain on startup.

    The in-process notification-email drain runs unless it is disabled
    (``NOTIFICATION_EMAIL_INPROCESS=false``), which is how a deploy hands the
    job to an external k8s CronJob instead.
    """
    run_startup_bootstrap()
    worker = None
    if settings.NOTIFICATION_EMAIL_INPROCESS:
        worker = EmailOutboxWorker()
        worker.start()
    try:
        yield
    finally:
        if worker is not None:
            worker.stop()


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

    app.state.limiter = limiter
    app.add_exception_handler(AppExceptionError, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(RateLimitExceeded, ratelimit_exception_handler)
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
    app.include_router(resources_router, prefix="/api/v1")
    app.include_router(requests_router, prefix="/api/v1")
    app.include_router(contributions_router, prefix="/api/v1")
    app.include_router(shipments_router, prefix="/api/v1")
    app.include_router(uploads_router, prefix="/api/v1")
    app.include_router(activity_router, prefix="/api/v1")
    app.include_router(comments_router, prefix="/api/v1")
    app.include_router(notices_router, prefix="/api/v1")
    app.include_router(notifications_router, prefix="/api/v1")
    app.include_router(watches_router, prefix="/api/v1")
    app.include_router(tracking_router, prefix="/api/v1")
    app.include_router(track_public_router, prefix="/api/v1")

    # Serve locally stored uploads. With an S3-compatible backend the
    # bucket serves files directly, so this mount is local-only.
    if settings.STORAGE_BACKEND == "local":
        media_root = Path(settings.MEDIA_ROOT)
        media_root.mkdir(parents=True, exist_ok=True)
        app.mount("/media", StaticFiles(directory=media_root), name="media")

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
