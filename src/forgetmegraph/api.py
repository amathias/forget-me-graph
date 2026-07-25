import uvicorn
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from forgetmegraph import __version__
from forgetmegraph.config import Settings
from forgetmegraph.context.datahub import probe_datahub
from forgetmegraph.demo.seed import DEMO_SECRET, MARKER
from forgetmegraph.privacy.selector import SelectorProtectionError, validate_selector_secret
from forgetmegraph.ui.router import router as ui_router

app = FastAPI(
    title="Forget-Me-Graph",
    version=__version__,
    description="Verified deletion and clean-retraining orchestration powered by DataHub.",
)


@app.exception_handler(RequestValidationError)
async def sanitized_validation_error(
    _request: Request,
    _error: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "request validation failed"})


@app.get("/api/health")
def health() -> dict[str, str]:
    settings = Settings.from_env()
    return {
        "status": "ok",
        "version": __version__,
        "project": settings.project_slug,
    }


def _selector_protection_ready(settings: Settings) -> bool:
    secret = settings.selector_secret
    if secret is None and settings.app_env in {"local", "test"}:
        secret = DEMO_SECRET
    if secret is None:
        return False
    try:
        validate_selector_secret(secret)
    except SelectorProtectionError:
        return False
    return True


@app.get("/api/readiness")
async def readiness(response: Response) -> dict[str, object]:
    settings = Settings.from_env()
    fixture_ready = (settings.demo_fixture_root / MARKER).is_file()
    selector_protection_ready = _selector_protection_ready(settings)

    datahub = await probe_datahub(settings)
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
        "project": settings.project_slug,
        "checks": {
            "fixture": "ready" if fixture_ready else "missing",
            "selector_protection": ("ready" if selector_protection_ready else "missing_or_invalid"),
            "datahub_gms": datahub.gms,
            "datahub_mcp": datahub.mcp,
            "datahub_catalog": datahub.catalog,
            "datahub_capabilities": datahub.capabilities,
        },
        "blockers": blockers,
    }


app.include_router(ui_router)


def run() -> None:
    settings = Settings.from_env()
    uvicorn.run(
        "forgetmegraph.api:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )
