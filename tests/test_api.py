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
            capabilities=["get_entities", "get_lineage"],
        )

    monkeypatch.setattr("forgetmegraph.api.probe_datahub", successful_probe)

    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["checks"]["datahub_gms"] == "connected"
    assert response.json()["checks"]["datahub_mcp"] == "connected"
    assert response.json()["checks"]["datahub_capabilities"] == [
        "get_entities",
        "get_lineage",
    ]
