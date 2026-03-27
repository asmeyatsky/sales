"""
FastAPI application factory.

Creates and configures the Searce Scout REST API application with all
routers, middleware, and the DI container wired into app.state.
"""

from __future__ import annotations

import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from searce_scout.scout_orchestrator.config.dependency_injection import Container
from searce_scout.scout_orchestrator.config.settings import ScoutSettings
from searce_scout.shared_kernel.errors import DomainError, ValidationError

from searce_scout.presentation.api.middleware.audit_log import AuditLogMiddleware
from searce_scout.presentation.api.middleware.auth import api_key_auth
from searce_scout.presentation.api.routes.accounts import router as accounts_router
from searce_scout.presentation.api.routes.crm import router as crm_router
from searce_scout.presentation.api.routes.messaging import router as messaging_router
from searce_scout.presentation.api.routes.outreach import router as outreach_router
from searce_scout.presentation.api.routes.presentations import (
    router as presentations_router,
)
from searce_scout.presentation.api.routes.stakeholders import (
    router as stakeholders_router,
)


def create_app(settings: ScoutSettings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        settings: Optional ScoutSettings; loaded from environment if not provided.

    Returns:
        A fully configured FastAPI instance with all routers mounted.
    """
    if settings is None:
        settings = ScoutSettings()

    container = Container(settings)

    app = FastAPI(
        title="Searce Scout API",
        description="Autonomous AI Sales Agent - Research, Outreach, and CRM Sync",
        version="1.0.0",
    )

    # Store container and settings in app.state for access in routes
    app.state.container = container
    app.state.settings = settings
    app.state.start_time = time.monotonic()

    # -- Middleware: CORS ---------------------------------------------------
    # NOTE: In production, configure SCOUT_ALLOWED_ORIGINS to restrict access.

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["X-API-Key", "Content-Type"],
    )

    # -- Middleware: Audit logging (SOC 2) ----------------------------------

    app.add_middleware(AuditLogMiddleware)

    # -- Middleware: Security headers ---------------------------------------

    @app.middleware("http")
    async def security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Cache-Control"] = "no-store"
        return response

    # -- Middleware: API key auth -------------------------------------------

    @app.middleware("http")
    async def auth_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        # Skip auth for docs and health endpoints
        if request.url.path in ("/docs", "/openapi.json", "/redoc", "/health", "/api/v1/metrics"):
            return await call_next(request)
        await api_key_auth(request, settings)
        return await call_next(request)

    # -- Request size limits -----------------------------------------------
    # FastAPI does not provide a built-in request body size limit.
    # For production deployments, enforce limits at the reverse-proxy or
    # uvicorn level, e.g.:
    #   uvicorn ... --limit-concurrency 100 --limit-max-requests 10000
    #   nginx: client_max_body_size 1m;

    # -- Exception handlers ------------------------------------------------

    @app.exception_handler(DomainError)
    async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "error_code": "DOMAIN_ERROR"},
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"detail": str(exc), "error_code": "VALIDATION_ERROR"},
        )

    # -- Routes ------------------------------------------------------------

    app.include_router(accounts_router)
    app.include_router(stakeholders_router)
    app.include_router(messaging_router)
    app.include_router(outreach_router)
    app.include_router(presentations_router)
    app.include_router(crm_router)

    # -- Health check ------------------------------------------------------

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/metrics", tags=["health"])
    async def metrics() -> dict:
        """Return service health metrics."""
        return {
            "status": "healthy",
            "version": "1.0.0",
            "uptime_seconds": time.monotonic() - app.state.start_time,
        }

    return app
