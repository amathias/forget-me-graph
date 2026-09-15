from __future__ import annotations

import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from forgetmegraph import __version__
from forgetmegraph.config import AppEnvironment, Settings
from forgetmegraph.demo.seed import DEMO_SECRET, MARKER
from forgetmegraph.errors import IntegrationFailure, PolicyViolation, StalePlanError
from forgetmegraph.privacy.selector import SelectorProtectionError, validate_selector_secret
from forgetmegraph.services import ApplicationServices, default_application_services
from forgetmegraph.ui.abuse import DemoAbuseGuard
from forgetmegraph.ui.router import router as ui_router


def _interactive_docs_enabled(app_env: AppEnvironment | str) -> bool:
    return app_env in {AppEnvironment.LOCAL, AppEnvironment.TEST}


def _selector_protection_ready(settings: Settings) -> bool:
    secret = settings.selector_secret
    if secret is None and settings.app_env in {AppEnvironment.LOCAL, AppEnvironment.TEST}:
        secret = DEMO_SECRET
    if secret is None:
        return False
    try:
        validate_selector_secret(secret)
    except SelectorProtectionError:
        return False
    return True


def create_app(
    settings: Settings | None = None,
    *,
    services: ApplicationServices | None = None,
) -> FastAPI:
    """Create one application with immutable settings and isolated process-local state."""

    app_settings = settings or Settings.from_env()
    app_services = services or default_application_services()
    docs_enabled = _interactive_docs_enabled(app_settings.app_env)
    application = FastAPI(
        title="Forget-Me-Graph",
        version=__version__,
        description="Verified deletion and clean-retraining orchestration powered by DataHub.",
        docs_url="/docs" if docs_enabled else None,
        redoc_url="/redoc" if docs_enabled else None,
        openapi_url="/openapi.json" if docs_enabled else None,
    )
    application.state.settings = app_settings
    application.state.services = app_services
    application.state.demo_guard = DemoAbuseGuard()

    def apply_public_security_headers(request: Request, response: Response) -> Response:
        if docs_enabled:
            return response
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "connect-src 'self'; "
            "object-src 'none'; "
            "base-uri 'none'; "
            "frame-ancestors 'none'; "
            "form-action 'self'"
        )
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        if request.url.path.startswith("/api/demo/"):
            response.headers["Cache-Control"] = "no-store"
        return response

    @application.middleware("http")
    async def public_security_headers(request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        return apply_public_security_headers(request, response)

    @application.exception_handler(RequestValidationError)
    async def sanitized_validation_error(
        _request: Request,
        _error: RequestValidationError,
    ) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": "request validation failed"})

    @application.exception_handler(StalePlanError)
    async def stale_plan_error(_request: Request, _error: StalePlanError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"detail": "the confirmed plan is stale"})

    @application.exception_handler(IntegrationFailure)
    async def integration_error(_request: Request, _error: IntegrationFailure) -> JSONResponse:
        return JSONResponse(
            status_code=503, content={"detail": "the live DataHub gate failed closed"}
        )

    @application.exception_handler(PolicyViolation)
    async def policy_error(_request: Request, _error: PolicyViolation) -> JSONResponse:
        return JSONResponse(
            status_code=400, content={"detail": "the request was refused by policy"}
        )

    @application.exception_handler(Exception)
    async def unexpected_error(request: Request, _error: Exception) -> Response:
        response = JSONResponse(
            status_code=500,
            content={"detail": "the request could not be completed"},
        )
        return apply_public_security_headers(request, response)

    @application.get("/api/health")
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": __version__,
            "project": app_settings.project_slug,
        }

    @application.get("/api/readiness")
    async def readiness(response: Response) -> dict[str, object]:
        fixture_ready = (app_settings.demo_fixture_root / MARKER).is_file()
        selector_protection_ready = _selector_protection_ready(app_settings)
        datahub = await app_services.datahub_probe(app_settings)
        blockers: list[str] = []
        if not fixture_ready:
            blockers.append("demo fixture is not seeded")
        if not selector_protection_ready:
            blockers.append("selector protection is missing or invalid")
        if not datahub.ready:
            blockers.append(datahub.blocker or "DataHub readiness verification failed")
        ready = not blockers
        if not ready:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "ready": ready,
            "project": app_settings.project_slug,
            "checks": {
                "fixture": "ready" if fixture_ready else "missing",
                "selector_protection": (
                    "ready" if selector_protection_ready else "missing_or_invalid"
                ),
                "datahub_gms": datahub.gms,
                "datahub_mcp": datahub.mcp,
                "datahub_catalog": datahub.catalog,
                "datahub_capabilities": datahub.capabilities,
            },
            "blockers": blockers,
        }

    application.include_router(ui_router)
    return application


app = create_app()


def run() -> None:
    settings: Settings = app.state.settings
    uvicorn.run(
        app,
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )
