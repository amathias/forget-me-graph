from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from forgetmegraph.api import create_app
from forgetmegraph.config import AppEnvironment, ConfigurationError, Settings
from forgetmegraph.services import default_application_services
from forgetmegraph.ui.router import DemoRunRequest

BASE_SETTINGS = Settings.from_env()


def _settings(**changes) -> Settings:
    return replace(BASE_SETTINGS, app_env=AppEnvironment.TEST, **changes)


def _production_settings(**changes) -> Settings:
    values = {
        "app_env": AppEnvironment.PRODUCTION,
        "selector_secret": "production-ui-test-secret",
        "datahub_gms_url": "https://datahub.example.test",
        "datahub_mcp_url": "https://datahub.example.test/mcp",
        "datahub_token": "test-only-token",
    }
    values.update(changes)
    return replace(BASE_SETTINGS, **values)


def _client(settings: Settings | None = None, *, services=None) -> TestClient:
    return TestClient(create_app(settings or _settings(), services=services))


def _plan_request(selector_value: str = "42") -> dict[str, str]:
    return {
        "request_id": "ui-safety-test",
        "selector_value": selector_value,
    }


def test_judge_console_serves_local_assets_and_exact_graph() -> None:
    client = _client()

    page = client.get("/")
    stylesheet = client.get("/assets/app.css")
    script = client.get("/assets/app.js")
    overview = client.get("/api/demo/overview")

    assert page.status_code == stylesheet.status_code == script.status_code == 200
    assert "Forget-Me-Graph" in page.text
    assert "Evidence Console" in page.text
    assert "PUBLIC DEMO" in page.text
    assert "synthetic subject <code>42</code>" in page.text
    assert "Never enter personal data" in page.text
    assert "confirmation-form" in page.text
    assert "Self-asserted operator label" in page.text
    assert "external model access" in page.text.lower()
    assert "requestJson" in script.text
    assert "card.className = `node-card" in script.text
    assert ".node-card" in stylesheet.text
    assert 'toast.classList.add("visible")' in script.text
    assert ".toast.visible" in stylesheet.text
    assert "localStorage" not in script.text
    assert "sessionStorage" not in script.text
    assert "console.log" not in script.text
    assert "https://" not in stylesheet.text
    assert 'result.status === "incomplete"' in script.text
    assert "Workflow incomplete. Review failed or blocked evidence." in script.text
    assert 'id="certificate-seal-mark"' in page.text
    assert 'incomplete ? "!" : "✓"' in script.text
    assert '.certificate-card[data-state="failed"] .certificate-seal span' in stylesheet.text
    assert "resultPhaseState" in script.text
    assert overview.status_code == 200
    assert overview.json()["namespace"] == "forgetme."
    assert len(overview.json()["nodes"]) == 10
    assert len(overview.json()["edges"]) == 9
    assert "Synthetic Subject" not in overview.text
    assert (
        overview.json()["coordinator_evidence"]["primary_guarded_run"]["certificate_sha256"]
        == "0dfc8e519e3cb3d30e037aa46b1b030e06a67d061023ec19ff70a93e61d78e1"
    )


def test_demo_plan_returns_only_protected_selector_and_bound_hash() -> None:
    selector_value = "731947"
    response = _client().post("/api/demo/plan", json=_plan_request(selector_value))

    assert response.status_code == 200
    payload = response.json()
    assert payload["selector"]["token"].startswith("subj_")
    assert payload["selector"]["raw_value_persisted"] is False
    assert len(payload["plan_hash"]) == 64
    assert len(payload["decisions"]) == 10
    assert "selector_value" not in response.text
    assert f'"{selector_value}"' not in response.text


def test_validation_error_does_not_echo_rejected_selector() -> None:
    raw_value = "private-selector-do-not-echo"
    response = _client().post("/api/demo/plan", json=_plan_request(raw_value))

    assert response.status_code == 422
    assert response.json() == {"detail": "request validation failed"}
    assert raw_value not in response.text


def test_demo_run_requires_explicit_plan_confirmation(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixture"
    client = _client(_settings(demo_fixture_root=fixture_root))
    plan = client.post("/api/demo/plan", json=_plan_request()).json()
    response = client.post(
        "/api/demo/run",
        json={
            **_plan_request(),
            "plan_hash": plan["plan_hash"],
            "confirmed_by": "test-privacy-operator",
            "confirmed": False,
            "reset_synthetic_estate": True,
            "require_datahub": False,
        },
    )

    assert response.status_code == 403
    assert not fixture_root.exists()


def test_demo_run_accepts_legacy_approval_field_names() -> None:
    payload = DemoRunRequest.model_validate(
        {
            **_plan_request(),
            "plan_hash": "0" * 64,
            "approver": "legacy-client",
            "approved": True,
        }
    )

    assert payload.confirmed_by == "legacy-client"
    assert payload.confirmed is True


def test_stale_plan_is_rejected_before_fixture_reset(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixture"
    response = _client(_settings(demo_fixture_root=fixture_root)).post(
        "/api/demo/run",
        json={
            **_plan_request(),
            "plan_hash": "0" * 64,
            "confirmed_by": "test-privacy-operator",
            "confirmed": True,
            "reset_synthetic_estate": True,
            "require_datahub": False,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "the confirmed plan is stale"
    assert not fixture_root.exists()


def test_local_confirmed_run_returns_and_downloads_redacted_evidence(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixture"
    client = _client(_settings(demo_fixture_root=fixture_root))
    plan = client.post("/api/demo/plan", json=_plan_request()).json()
    response = client.post(
        "/api/demo/run",
        json={
            **_plan_request(),
            "plan_hash": plan["plan_hash"],
            "confirmed_by": "test-privacy-operator",
            "confirmed": True,
            "reset_synthetic_estate": True,
            "require_datahub": False,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "verified_with_limitations"
    assert payload["plan_hash"] == plan["plan_hash"]
    assert payload["selector_token"].startswith("subj_")
    assert payload["datahub_required"] is False
    assert len(payload["items"]) == 10
    assert payload["evidence"]["certificate.json"]["sha256"]
    assert payload["evidence"]["certificate.md"]["sha256"]
    assert "selector_value" not in response.text
    assert "Synthetic Subject" not in response.text

    certificate = client.get(payload["evidence"]["certificate.json"]["download_url"])
    markdown = client.get(payload["evidence"]["certificate.md"]["download_url"])

    assert certificate.status_code == markdown.status_code == 200
    assert "Synthetic Subject" not in certificate.text
    assert "Synthetic Subject" not in markdown.text
    assert not (fixture_root / "evidence" / "ui-safety-test" / "selector.json").exists()


def test_evidence_download_rejects_unallowlisted_paths(tmp_path: Path) -> None:
    response = _client(_settings(demo_fixture_root=tmp_path)).get(
        "/api/demo/evidence/ui-safety-test/selector.json"
    )

    assert response.status_code == 404


def test_nonlocal_ui_run_cannot_disable_live_datahub_gate(tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixture"
    observed: dict[str, object] = {}

    def fake_run_workflow(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            request_id=kwargs["request_id"],
            selector_token="subj_protected",
            plan_hash=kwargs["expected_plan_hash"],
            status=SimpleNamespace(value="verified"),
            certificate_hash="f" * 64,
            generated_at=datetime.now(UTC),
            items=[],
        )

    services = replace(default_application_services(), run_workflow=fake_run_workflow)
    client = _client(_production_settings(demo_fixture_root=fixture_root), services=services)
    plan = client.post("/api/demo/plan", json=_plan_request()).json()
    response = client.post(
        "/api/demo/run",
        json={
            **_plan_request(),
            "plan_hash": plan["plan_hash"],
            "confirmed_by": "test-privacy-operator",
            "confirmed": True,
            "reset_synthetic_estate": False,
            "require_datahub": False,
        },
    )

    assert response.status_code == 200
    assert observed["require_datahub"] is True
    assert observed["confirmed_by"] == "test-privacy-operator"


def test_nonlocal_app_creation_fails_without_selector_secret() -> None:
    with pytest.raises(ConfigurationError, match="non-local"):
        _production_settings(selector_secret=None)


def test_public_plan_rejects_any_selector_outside_fixed_synthetic_subject() -> None:
    response = _client(_production_settings()).post(
        "/api/demo/plan",
        json=_plan_request("41"),
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "the public demo accepts only its documented synthetic subject"
    }


def test_public_plan_returns_retry_after_when_client_limit_is_reached() -> None:
    client = _client(_production_settings(demo_plan_client_limit_per_minute=1))

    assert client.post("/api/demo/plan", json=_plan_request()).status_code == 200
    response = client.post("/api/demo/plan", json=_plan_request())

    assert response.status_code == 429
    assert response.headers["retry-after"]
    assert response.json()["detail"] == "the public demo is busy; retry after the indicated delay"
