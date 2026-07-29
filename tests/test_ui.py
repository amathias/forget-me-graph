from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from forgetmegraph.api import app
from forgetmegraph.ui.router import _demo_guard


def _client() -> TestClient:
    return TestClient(app)


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
    assert "approval-form" in page.text
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


def test_demo_run_requires_explicit_approval(monkeypatch, tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixture"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_FIXTURE_ROOT", str(fixture_root))
    plan = _client().post("/api/demo/plan", json=_plan_request()).json()

    response = _client().post(
        "/api/demo/run",
        json={
            **_plan_request(),
            "plan_hash": plan["plan_hash"],
            "approver": "test-privacy-operator",
            "approved": False,
            "reset_synthetic_estate": True,
            "require_datahub": False,
        },
    )

    assert response.status_code == 403
    assert not fixture_root.exists()


def test_stale_plan_is_rejected_before_fixture_reset(monkeypatch, tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixture"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_FIXTURE_ROOT", str(fixture_root))

    response = _client().post(
        "/api/demo/run",
        json={
            **_plan_request(),
            "plan_hash": "0" * 64,
            "approver": "test-privacy-operator",
            "approved": True,
            "reset_synthetic_estate": True,
            "require_datahub": False,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "the approved plan is stale"
    assert not fixture_root.exists()


def test_local_approved_run_returns_and_downloads_redacted_evidence(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fixture_root = tmp_path / "fixture"
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("DEMO_FIXTURE_ROOT", str(fixture_root))
    client = _client()
    plan = client.post("/api/demo/plan", json=_plan_request()).json()

    response = client.post(
        "/api/demo/run",
        json={
            **_plan_request(),
            "plan_hash": plan["plan_hash"],
            "approver": "test-privacy-operator",
            "approved": True,
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


def test_evidence_download_rejects_unallowlisted_paths(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DEMO_FIXTURE_ROOT", str(tmp_path))

    response = _client().get("/api/demo/evidence/ui-safety-test/selector.json")

    assert response.status_code == 404


def test_nonlocal_ui_run_cannot_disable_live_datahub_gate(monkeypatch, tmp_path: Path) -> None:
    fixture_root = tmp_path / "fixture"
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FMG_SELECTOR_SECRET", "production-ui-test-secret")
    monkeypatch.setenv("DEMO_FIXTURE_ROOT", str(fixture_root))
    plan = _client().post("/api/demo/plan", json=_plan_request()).json()
    observed: dict[str, object] = {}

    def fake_run_workflow(**kwargs):
        observed.update(kwargs)
        return SimpleNamespace(
            request_id=kwargs["request_id"],
            selector_token=plan["selector"]["token"],
            plan_hash=plan["plan_hash"],
            status=SimpleNamespace(value="verified"),
            certificate_hash="f" * 64,
            generated_at=datetime.now(UTC),
            items=[],
        )

    monkeypatch.setattr("forgetmegraph.ui.router.run_workflow", fake_run_workflow)

    response = _client().post(
        "/api/demo/run",
        json={
            **_plan_request(),
            "plan_hash": plan["plan_hash"],
            "approver": "test-privacy-operator",
            "approved": True,
            "reset_synthetic_estate": False,
            "require_datahub": False,
        },
    )

    assert response.status_code == 200
    assert observed["require_datahub"] is True


def test_nonlocal_plan_fails_closed_without_selector_secret(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("FMG_SELECTOR_SECRET", raising=False)

    response = _client().post("/api/demo/plan", json=_plan_request())

    assert response.status_code == 400
    assert response.json() == {"detail": "the deterministic plan could not be built"}
    assert "selector protection" not in response.text


def test_public_plan_rejects_any_selector_outside_fixed_synthetic_subject(monkeypatch) -> None:
    _demo_guard.reset()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FMG_SELECTOR_SECRET", "production-ui-test-secret")

    response = _client().post("/api/demo/plan", json=_plan_request("41"))

    assert response.status_code == 400
    assert response.json() == {
        "detail": "the public demo accepts only its documented synthetic subject"
    }


def test_public_plan_returns_retry_after_when_client_limit_is_reached(monkeypatch) -> None:
    _demo_guard.reset()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("FMG_SELECTOR_SECRET", "production-ui-test-secret")
    monkeypatch.setenv("DEMO_PLAN_CLIENT_LIMIT_PER_MINUTE", "1")
    client = _client()

    assert client.post("/api/demo/plan", json=_plan_request()).status_code == 200
    response = client.post("/api/demo/plan", json=_plan_request())

    assert response.status_code == 429
    assert response.headers["retry-after"]
    assert response.json()["detail"] == "the public demo is busy; retry after the indicated delay"
