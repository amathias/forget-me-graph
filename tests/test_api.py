import pytest
from fastapi.testclient import TestClient

from forgetmegraph.api import _interactive_docs_enabled, app
from forgetmegraph.context.datahub import DataHubCapabilityStatus


def test_coordinator_health_contract() -> None:
    response = TestClient(app).get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["project"] == "forget-me-graph"


def test_interactive_api_docs_are_local_only() -> None:
    assert _interactive_docs_enabled("local") is True
    assert _interactive_docs_enabled("test") is True
    assert _interactive_docs_enabled("hackathon") is False
    assert _interactive_docs_enabled("production") is False


def test_nonlocal_responses_include_security_headers(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")

    response = TestClient(app).get("/api/demo/overview")

    assert response.status_code == 200
    assert response.headers["content-security-policy"].startswith("default-src 'self'")
    assert response.headers["strict-transport-security"] == "max-age=31536000"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"


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


def _configure_other_readiness_gates(monkeypatch, tmp_path) -> None:
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


def test_readiness_fails_closed_without_nonlocal_selector_secret(monkeypatch, tmp_path) -> None:
    _configure_other_readiness_gates(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("FMG_SELECTOR_SECRET", raising=False)

    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert response.json()["checks"]["selector_protection"] == "missing_or_invalid"
    assert response.json()["blockers"] == ["selector protection is missing or invalid"]


def test_readiness_fails_closed_for_short_selector_secret(monkeypatch, tmp_path) -> None:
    _configure_other_readiness_gates(monkeypatch, tmp_path)
    invalid_secret = "fifteen-chars!!"
    assert len(invalid_secret) == 15
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FMG_SELECTOR_SECRET", invalid_secret)

    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert response.json()["checks"]["selector_protection"] == "missing_or_invalid"
    assert response.json()["blockers"] == ["selector protection is missing or invalid"]
    assert invalid_secret not in response.text


def test_readiness_accepts_minimum_valid_selector_secret(monkeypatch, tmp_path) -> None:
    _configure_other_readiness_gates(monkeypatch, tmp_path)
    minimum_valid_secret = "sixteen-chars!!!"
    assert len(minimum_valid_secret) == 16
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FMG_SELECTOR_SECRET", minimum_valid_secret)

    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["checks"]["selector_protection"] == "ready"
    assert response.json()["blockers"] == []
    assert minimum_valid_secret not in response.text


@pytest.mark.parametrize("app_env", ["local", "test"])
def test_readiness_accepts_local_test_demo_secret_fallback(
    monkeypatch,
    tmp_path,
    app_env,
) -> None:
    _configure_other_readiness_gates(monkeypatch, tmp_path)
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.delenv("FMG_SELECTOR_SECRET", raising=False)

    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["checks"]["selector_protection"] == "ready"
    assert response.json()["blockers"] == []


@pytest.mark.parametrize("app_env", ["local", "test"])
def test_readiness_does_not_mask_explicit_invalid_local_test_secret(
    monkeypatch,
    tmp_path,
    app_env,
) -> None:
    _configure_other_readiness_gates(monkeypatch, tmp_path)
    invalid_secret = "too-short"
    monkeypatch.setenv("APP_ENV", app_env)
    monkeypatch.setenv("FMG_SELECTOR_SECRET", invalid_secret)

    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert response.json()["checks"]["selector_protection"] == "missing_or_invalid"
    assert response.json()["blockers"] == ["selector protection is missing or invalid"]
    assert invalid_secret not in response.text
