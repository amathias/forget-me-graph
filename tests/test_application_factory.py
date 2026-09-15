from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from forgetmegraph.api import create_app
from forgetmegraph.config import AppEnvironment, ConfigurationError, Settings
from forgetmegraph.errors import IntegrationFailure, PolicyViolation, StalePlanError
from forgetmegraph.services import default_application_services


def _local_settings(**changes) -> Settings:
    settings = Settings.from_env()
    return replace(settings, app_env=AppEnvironment.LOCAL, **changes)


def _production_settings(**changes) -> Settings:
    settings = Settings.from_env()
    values = {
        "app_env": AppEnvironment.PRODUCTION,
        "selector_secret": "production-factory-test-secret",
        "datahub_gms_url": "https://datahub.example.test",
        "datahub_mcp_url": "https://datahub.example.test/mcp",
        "datahub_token": "test-only-token",
    }
    values.update(changes)
    return replace(settings, **values)


def test_nonlocal_settings_require_valid_secret_and_datahub_configuration(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("FMG_SELECTOR_SECRET", raising=False)
    monkeypatch.delenv("DATAHUB_GMS_URL", raising=False)
    monkeypatch.delenv("DATAHUB_MCP_URL", raising=False)
    monkeypatch.delenv("DATAHUB_TOKEN", raising=False)

    with pytest.raises(ConfigurationError, match="non-local runtime configuration"):
        create_app()


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"datahub_gms_url": "not-a-url"}, "DATAHUB_GMS_URL"),
        ({"datahub_mcp_url": "ftp://datahub.example.test/mcp"}, "DATAHUB_MCP_URL"),
        ({"datahub_token": "   "}, "non-local runtime configuration"),
    ],
)
def test_nonlocal_settings_reject_invalid_datahub_configuration(changes, message) -> None:
    with pytest.raises(ConfigurationError, match=message):
        _production_settings(**changes)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("APP_PORT", "not-a-port"),
        ("APP_PORT", "70000"),
        ("DEMO_PLAN_CLIENT_LIMIT_PER_MINUTE", "zero"),
        ("DEMO_RUN_COOLDOWN_SECONDS", "0"),
    ],
)
def test_invalid_numeric_settings_fail_during_construction(monkeypatch, name, value) -> None:
    monkeypatch.setenv("APP_ENV", "local")
    monkeypatch.setenv(name, value)

    with pytest.raises(ConfigurationError, match=name):
        create_app()


def test_two_apps_keep_docs_headers_and_rate_state_isolated() -> None:
    local_app = create_app(_local_settings())
    production_settings = _production_settings(demo_plan_client_limit_per_minute=1)
    first_public_app = create_app(production_settings)
    second_public_app = create_app(production_settings)

    local = TestClient(local_app)
    first_public = TestClient(first_public_app)
    second_public = TestClient(second_public_app)

    assert local.get("/docs").status_code == 200
    assert first_public.get("/docs").status_code == 404
    assert "strict-transport-security" not in local.get("/api/demo/overview").headers
    assert first_public.get("/api/demo/overview").headers["strict-transport-security"]

    payload = {"request_id": "factory-isolation-test", "selector_value": "42"}
    assert first_public.post("/api/demo/plan", json=payload).status_code == 200
    assert first_public.post("/api/demo/plan", json=payload).status_code == 429
    assert second_public.post("/api/demo/plan", json=payload).status_code == 200


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_detail"),
    [
        (StalePlanError("message text can change"), 409, "the confirmed plan is stale"),
        (PolicyViolation("message text can change"), 400, "the request was refused by policy"),
        (
            IntegrationFailure("message text can change"),
            503,
            "the live DataHub gate failed closed",
        ),
        (RuntimeError("unexpected internal fault"), 500, "the request could not be completed"),
    ],
)
def test_typed_errors_have_message_independent_http_statuses(
    error,
    expected_status,
    expected_detail,
) -> None:
    def fail_workflow(**_kwargs):
        raise error

    services = replace(default_application_services(), run_workflow=fail_workflow)
    client = TestClient(
        create_app(_local_settings(), services=services),
        raise_server_exceptions=False,
    )

    response = client.post(
        "/api/demo/run",
        json={
            "request_id": "typed-error-test",
            "selector_value": "42",
            "plan_hash": "0" * 64,
            "confirmed_by": "test-operator",
            "confirmed": True,
            "reset_synthetic_estate": False,
            "require_datahub": False,
        },
    )

    assert response.status_code == expected_status
    if response.headers["content-type"].startswith("application/json"):
        assert response.json().get("detail") == expected_detail
    else:
        assert response.text == expected_detail


def test_unexpected_plan_fault_remains_a_server_error() -> None:
    def fail_plan(**_kwargs):
        raise RuntimeError("unexpected planning fault")

    services = replace(default_application_services(), prepare_workflow=fail_plan)
    client = TestClient(
        create_app(_production_settings(), services=services),
        raise_server_exceptions=False,
    )

    response = client.post(
        "/api/demo/plan",
        json={"request_id": "unexpected-plan-test", "selector_value": "42"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "the request could not be completed"}
    assert response.headers["content-security-policy"].startswith("default-src 'self'")
    assert response.headers["strict-transport-security"] == "max-age=31536000"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["cache-control"] == "no-store"
