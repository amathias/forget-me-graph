import uvicorn
from fastapi import FastAPI, Response, status

from forgetmegraph import __version__
from forgetmegraph.config import Settings
from forgetmegraph.demo.seed import MARKER

app = FastAPI(
    title="Forget-Me-Graph",
    version=__version__,
    description="Verified deletion and clean-retraining orchestration powered by DataHub.",
)


@app.get("/api/health")
def health() -> dict[str, str]:
    settings = Settings.from_env()
    return {
        "status": "ok",
        "version": __version__,
        "project": settings.project_slug,
    }


@app.get("/api/readiness")
def readiness(response: Response) -> dict[str, object]:
    settings = Settings.from_env()
    fixture_ready = (settings.demo_fixture_root / MARKER).is_file()
    datahub_configured = bool(
        settings.datahub_gms_url and settings.datahub_mcp_url and settings.datahub_token
    )
    blockers: list[str] = []
    if not fixture_ready:
        blockers.append("demo fixture is not seeded")
    if not datahub_configured:
        blockers.append("DataHub connection is not fully configured")
    if datahub_configured:
        blockers.append("live DataHub connectivity verification is not implemented")
    ready = not blockers
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {
        "ready": ready,
        "project": settings.project_slug,
        "checks": {
            "fixture": "ready" if fixture_ready else "missing",
            "datahub": "pending" if datahub_configured else "unconfigured",
        },
        "blockers": blockers,
    }


def run() -> None:
    settings = Settings.from_env()
    uvicorn.run(
        "forgetmegraph.api:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )
