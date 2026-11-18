"""FastAPI application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router
from app.core.config import PROJECT_TITLE, get_settings
from app.core.errors import ApplicationError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    settings = get_settings()
    warmup_task: asyncio.Task[object] | None = None
    if settings.embedding_warmup_enabled and settings.app_env != "test":
        from app.documents.embeddings import get_embedding_service

        async def warmup_embedding() -> None:
            try:
                await asyncio.to_thread(
                    get_embedding_service().embed,
                    ["khởi động tra cứu thông tin sức khỏe"],
                )
                logger.info("Embedding model warm-up completed")
            except Exception:
                logger.warning(
                    "Embedding model warm-up failed; lazy loading remains available",
                    exc_info=True,
                )

        warmup_task = asyncio.create_task(warmup_embedding())
        application.state.embedding_warmup_task = warmup_task
    yield
    if warmup_task is not None and not warmup_task.done():
        warmup_task.cancel()


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(title=PROJECT_TITLE, version="0.11.0", lifespan=lifespan)
    allowed_headers = ["Content-Type", "Authorization", "X-CSRF-Token"]
    if settings.app_env != "production":
        allowed_headers.append("X-Dev-User-Id")
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_origin],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=allowed_headers,
    )

    @application.exception_handler(ApplicationError)
    async def handle_application_error(_request: Request, exc: ApplicationError) -> JSONResponse:
        headers = None
        retry_after = getattr(exc, "retry_after_seconds", None)
        if retry_after is not None:
            headers = {"Retry-After": str(retry_after)}
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "detail": exc.detail}},
            headers=headers,
        )

    @application.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, _exc: Exception) -> JSONResponse:
        logger.error("Unhandled request error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_server_error",
                    "detail": "An unexpected server error occurred.",
                }
            },
        )

    @application.middleware("http")
    async def add_security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), geolocation=()"
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    application.include_router(router, prefix="/api/v1")
    return application


app = create_app()
