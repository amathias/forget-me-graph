from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from forgetmegraph.api import _interactive_docs_enabled, create_app
from forgetmegraph.config import AppEnvironment, ConfigurationError, Settings
from forgetmegraph.context.datahub import DataHubCapabilityStatus
from forgetmegraph.services import default_application_services

BASE_SETTINGS = Settings.from_env()


def _settings(**changes) -> Settings:
    return replace(BASE_SETTINGS, app_env=AppEnvironment.TEST, **changes)


def _production_settings(**changes) -> Settings:
    values = {
        "app_env": AppEnvironment.PRODUCTION,
        "selector_secret": "production-api-test-secret",
        "datahub_gms_url": "https://datahub.example.test",
        "datahub_mcp_url": "https://datahub.example.test/mcp",
        "datahub_token": "test-only-token",
    }
    values.update(changes)
    return replace(BASE_SETTINGS, **values)


def _services_with_probe(probe):
    return replace(default_application_services(), datahub_probe=probe)


def _seeded_fixture(tmp_path):
    fixture = tmp_path / "forget-me-graph"
    fixture.mkdir()
    (fixture / ".forgetmegraph-demo").write_text(
        "synthetic disposable demo artifacts\n",
        encoding="utf-8",
    )
    return fixture


async def _successful_probe(_settings):
    return DataHubCapabilityStatus(
        ready=True,
        gms="connected",
        mcp="connected",
        catalog="ready",
        capabilities=["get_entities", "get_lineage"],
    )


def test_coordinator_health_contract() -> None:
    response = TestClient(create_app(_settings())).get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["project"] == "forget-me-graph"


def test_interactive_api_docs_are_local_only() -> None:
    assert _interactive_docs_enabled("local") is True
    assert _interactive_docs_enabled("test") is True
    assert _interactive_docs_enabled("hackathon") is False
    assert _interactive_docs_enabled("production") is False


def test_app_environment_is_explicit_and_allowlisted(monkeypatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    with pytest.raises(ConfigurationError, match="APP_ENV is required"):
        Settings.from_env()

    monkeypatch.setenv("APP_ENV", "unexpected")
    with pytest.raises(ConfigurationError, match="must be one of"):
        Settings.from_env()

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FMG_SELECTOR_SECRET", "production-api-test-secret")
    monkeypatch.setenv("DATAHUB_GMS_URL", "https://datahub.example.test")
    monkeypatch.setenv("DATAHUB_MCP_URL", "https://datahub.example.test/mcp")
    monkeypatch.setenv("DATAHUB_TOKEN", "test-only-token")
    assert Settings.from_env().app_env is AppEnvironment.PRODUCTION


def test_nonlocal_responses_include_security_headers() -> None:
    response = TestClient(create_app(_production_settings())).get("/api/demo/overview")

    assert response.status_code == 200
    assert response.headers["content-security-policy"].startswith("default-src 'self'")
    assert response.headers["strict-transport-security"] == "max-age=31536000"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"


def test_readiness_fails_closed_without_fixture_or_datahub(tmp_path) -> None:
    async def failed_probe(_settings):
        return DataHubCapabilityStatus(
            ready=False,
            gms="disconnected",
            mcp="unverified",
            catalog="unverified",
            capabilities=[],
            blocker="DataHub is unavailable",
        )

    app = create_app(
        _settings(demo_fixture_root=tmp_path / "missing-fixture"),
        services=_services_with_probe(failed_probe),
    )
    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert response.json()["checks"]["fixture"] == "missing"


def test_readiness_returns_503_for_verified_soft_reset_state(tmp_path) -> None:
    fixture = _seeded_fixture(tmp_path)

    async def reset_catalog_probe(_settings):
        return DataHubCapabilityStatus(
            ready=False,
            gms="connected",
            mcp="unverified",
            catalog="missing_or_invalid",
            capabilities=[],
            blocker="DataHub catalog allocation is not seeded or valid",
        )

    app = create_app(
        _settings(demo_fixture_root=fixture),
        services=_services_with_probe(reset_catalog_probe),
    )
    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 503
    assert response.json()["ready"] is False
    assert response.json()["checks"]["datahub_catalog"] == "missing_or_invalid"
    assert response.json()["blockers"] == ["DataHub catalog allocation is not seeded or valid"]


def test_readiness_performs_live_capability_probe(tmp_path) -> None:
    fixture = _seeded_fixture(tmp_path)
    app = create_app(
        _settings(demo_fixture_root=fixture),
        services=_services_with_probe(_successful_probe),
    )

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


@pytest.mark.parametrize("invalid_secret", [None, "fifteen-chars!!"])
def test_nonlocal_app_creation_rejects_missing_or_short_selector_secret(invalid_secret) -> None:
    with pytest.raises(ConfigurationError, match="FMG_SELECTOR_SECRET|non-local"):
        _production_settings(selector_secret=invalid_secret)


def test_readiness_accepts_minimum_valid_selector_secret(tmp_path) -> None:
    minimum_valid_secret = "sixteen-chars!!!"
    assert len(minimum_valid_secret) == 16
    fixture = _seeded_fixture(tmp_path)
    app = create_app(
        _production_settings(
            selector_secret=minimum_valid_secret,
            demo_fixture_root=fixture,
        ),
        services=_services_with_probe(_successful_probe),
    )

    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["checks"]["selector_protection"] == "ready"
    assert response.json()["blockers"] == []
    assert minimum_valid_secret not in response.text


@pytest.mark.parametrize("app_env", [AppEnvironment.LOCAL, AppEnvironment.TEST])
def test_readiness_accepts_local_test_demo_secret_fallback(tmp_path, app_env) -> None:
    fixture = _seeded_fixture(tmp_path)
    app = create_app(
        replace(
            BASE_SETTINGS,
            app_env=app_env,
            selector_secret=None,
            demo_fixture_root=fixture,
        ),
        services=_services_with_probe(_successful_probe),
    )

    response = TestClient(app).get("/api/readiness")

    assert response.status_code == 200
    assert response.json()["ready"] is True
    assert response.json()["checks"]["selector_protection"] == "ready"
    assert response.json()["blockers"] == []


@pytest.mark.parametrize("app_env", [AppEnvironment.LOCAL, AppEnvironment.TEST])
def test_local_test_app_creation_rejects_explicit_invalid_secret(app_env) -> None:
    invalid_secret = "too-short"

    with pytest.raises(ConfigurationError, match="FMG_SELECTOR_SECRET"):
        replace(BASE_SETTINGS, app_env=app_env, selector_secret=invalid_secret)
