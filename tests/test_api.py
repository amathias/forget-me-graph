from fastapi.testclient import TestClient

from forgetmegraph.api import app


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
