from fastapi.testclient import TestClient

from forgetmegraph.api import app
from forgetmegraph.context.datahub import DataHubCapabilityStatus


def test_coordinator_health_contract() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["project"] == "forget-me-graph"


def test_readiness_fails_closed_without_fixture_or_datahub(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DEMO_FIXTURE_ROOT", str(tmp_path / "missing-fixture"))
    monkeypatch.delenv("DATAHUB_TOKEN", raising=False)

    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert response.json()["checks"]["fixture"] == "missing"


def test_readiness_returns_503_for_verified_soft_reset_state(monkeypatch, tmp_path) -> None:
    fixture = tmp_path / "forget-me-graph"
    fixture.mkdir()
    (fixture / ".forgetmegraph-demo").write_text("synthetic disposable demo artifacts\n")
    monkeypatch.setenv("DEMO_FIXTURE_ROOT", str(fixture))

    async def reset_catalog_probe(settings):
        return DataHubCapabilityStatus(
            ready=False,
            gms="connected",
            mcp="unverified",
            catalog="missing_or_invalid",
            capabilities=[],
            blocker="DataHub catalog allocation is not seeded or valid",
        )

    monkeypatch.setattr("forgetmegraph.api.probe_datahub", reset_catalog_probe)

    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert response.json()["checks"]["datahub_catalog"] == "missing_or_invalid"
    assert response.json()["blockers"] == ["DataHub catalog allocation is not seeded or valid"]


def test_readiness_performs_live_capability_probe(monkeypatch, tmp_path) -> None:
    fixture = tmp_path / "forget-me-graph"
    fixture.mkdir()
    (fixture / ".forgetmegraph-demo").write_text("synthetic disposable demo artifacts\n")
    monkeypatch.setenv("DEMO_FIXTURE_ROOT", str(fixture))

    async def successful_probe(settings):
        return DataHubCapabilityStatus(
            ready=True,
            gms="connected",
            mcp="connected",
            catalog="ready",
            capabilities=["get_entities", "get_lineage"],
        )

    monkeypatch.setattr("forgetmegraph.api.probe_datahub", successful_probe)

    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["checks"]["datahub_gms"] == "connected"
    assert response.json()["checks"]["datahub_mcp"] == "connected"
    assert response.json()["checks"]["datahub_catalog"] == "ready"
    assert response.json()["checks"]["datahub_capabilities"] == [
        "get_entities",
        "get_lineage",
    ]


def test_readiness_fails_closed_without_nonlocal_selector_secret(monkeypatch, tmp_path) -> None:
    fixture = tmp_path / "forget-me-graph"
    fixture.mkdir()
    (fixture / ".forgetmegraph-demo").write_text("synthetic disposable demo artifacts\n")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("DEMO_FIXTURE_ROOT", str(fixture))
    monkeypatch.delenv("FMG_SELECTOR_SECRET", raising=False)

    async def successful_probe(settings):
        return DataHubCapabilityStatus(
            ready=True,
            gms="connected",
            mcp="connected",
            catalog="ready",
            capabilities=["get_entities", "get_lineage"],
        )

    monkeypatch.setattr("forgetmegraph.api.probe_datahub", successful_probe)

    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 503
    assert response.json()["checks"]["selector_protection"] == "missing"
    assert response.json()["blockers"] == ["selector protection is not configured"]
