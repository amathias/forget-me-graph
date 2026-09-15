import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest

from forgetmegraph.context.provider import FixtureContextProvider
from forgetmegraph.demo.seed import inspect_presence, seed_estate
from forgetmegraph.domain.models import SubjectSelector
from forgetmegraph.execution.engine import execute_plan
from forgetmegraph.execution.models import (
    ExecutionReceipt,
    PlanConfirmation,
    ReceiptStatus,
    execution_idempotency_key,
)
from forgetmegraph.execution.safety import SafetyViolation, require_namespace
from forgetmegraph.planning.mappings import MappingRegistry
from forgetmegraph.planning.planner import build_action_plan
from forgetmegraph.privacy.selector import SelectorProtector
from forgetmegraph.verification.certificate import (
    CertificateStatus,
    ItemStatus,
    canonical_certificate_payload,
    verify_and_certify,
    verify_certificate,
    verify_certificate_file,
)
from forgetmegraph.verification.certificate import main as verify_certificate_main

PROJECT_ROOT = Path(__file__).parents[1]
CUSTOMERS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)"
TICKETS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.tickets,PROD)"
SECRET = "a-test-secret-that-is-long-enough"


def _build_fixture_plan(*, selector_value: str = "42"):
    context = FixtureContextProvider(PROJECT_ROOT / "demo/metadata/graph.json")
    protector = SelectorProtector(SECRET)
    selector = protector.protect(
        SubjectSelector(subject_type="customer", field="customer_id", value=selector_value)
    )
    plan = build_action_plan(
        request_id="req-execution-test",
        selector=selector,
        entrypoint_urns=[CUSTOMERS, TICKETS],
        artifacts=context.artifacts(),
        edges=context.downstream_edges(),
        mappings=MappingRegistry.from_json(PROJECT_ROOT / "demo/selector-mappings.json"),
    )
    return context, protector, selector, plan


def test_stale_plan_confirmation_is_rejected_before_execution(tmp_path) -> None:
    context, protector, selector, plan = _build_fixture_plan()
    confirmation = PlanConfirmation.grant(plan, confirmed_by="privacy-operator").model_copy(
        update={"plan_hash": "0" * 64}
    )

    with pytest.raises(SafetyViolation, match="stale"):
        execute_plan(
            root=tmp_path / "not-used",
            plan=plan,
            confirmation=confirmation,
            selector=selector,
            protector=protector,
            artifacts=context.artifacts(),
            selector_secret=SECRET,
        )


def test_namespace_guard_rejects_cross_project_target() -> None:
    _, _, _, plan = _build_fixture_plan()
    decision = plan.decisions[0].model_copy(
        update={"target_urn": "urn:li:dataset:(urn:li:dataPlatform:duckdb,other.raw,PROD)"}
    )
    unsafe_plan = plan.model_copy(update={"decisions": [decision, *plan.decisions[1:]]})

    with pytest.raises(SafetyViolation, match="outside"):
        require_namespace(unsafe_plan, "forgetme.")


def test_namespace_guard_rejects_prefix_embedded_outside_dataset_name() -> None:
    _, _, _, plan = _build_fixture_plan()
    decision = plan.decisions[0].model_copy(
        update={
            "target_urn": (
                "urn:li:dataset:(urn:li:dataPlatform:forgetme.duckdb,other.raw.data,PROD)"
            )
        }
    )
    unsafe_plan = plan.model_copy(update={"decisions": [decision, *plan.decisions[1:]]})

    with pytest.raises(SafetyViolation, match="outside"):
        require_namespace(unsafe_plan, "forgetme.")


def test_confirmed_workflow_purges_retrains_verifies_and_is_idempotent(tmp_path) -> None:
    root = tmp_path / "fixtures" / "forget-me-graph"
    seed_estate(root, selector_secret=SECRET)
    context, protector, selector, plan = _build_fixture_plan()
    confirmation = PlanConfirmation.grant(plan, confirmed_by="privacy-operator")

    receipts = execute_plan(
        root=root,
        plan=plan,
        confirmation=confirmation,
        selector=selector,
        protector=protector,
        artifacts=context.artifacts(),
        selector_secret=SECRET,
    )

    assert len(receipts) == 9
    assert all(receipt.status is ReceiptStatus.SUCCEEDED for receipt in receipts)
    after = inspect_presence(root, customer_id=42, selector_secret=SECRET)
    assert all(count == 0 for count in after["artifacts"].values())
    manifest = json.loads((root / "active_model_manifest.json").read_text(encoding="utf-8"))
    assert manifest["model_version"] == "model-v2"
    assert manifest["training_snapshot"] == "training_snapshot_v2.csv"
    assert (root / "retired_model-v1_manifest.json").is_file()
    confirmation_path = root / "evidence/req-execution-test/plan_confirmation.json"
    assert json.loads(confirmation_path.read_text())["plan_hash"] == plan.plan_hash

    certificate = verify_and_certify(
        root=root,
        plan=plan,
        selector=selector,
        protector=protector,
        artifacts=context.artifacts(),
        receipts=receipts,
        selector_secret=SECRET,
    )
    assert certificate.status is CertificateStatus.VERIFIED_WITH_LIMITATIONS
    assert any(item.status is ItemStatus.EXEMPT for item in certificate.items)
    assert all(
        item.status in {ItemStatus.VERIFIED, ItemStatus.EXEMPT} for item in certificate.items
    )
    certificate_path = root / "evidence/req-execution-test/certificate.json"
    assert certificate_path.is_file()
    assert (root / "evidence/req-execution-test/certificate.md").is_file()
    assert verify_certificate(certificate) is True
    assert (
        json.loads(canonical_certificate_payload(certificate))["hash_schema"]
        == "forgetme-certificate-v1"
    )
    assert verify_certificate_file(certificate_path) == certificate
    assert verify_certificate_main([str(certificate_path)]) == 0

    repeated = execute_plan(
        root=root,
        plan=plan,
        confirmation=confirmation,
        selector=selector,
        protector=protector,
        artifacts=context.artifacts(),
        selector_secret=SECRET,
    )
    assert [item.receipt_id for item in repeated] == [item.receipt_id for item in receipts]


def test_same_request_different_plan_does_not_reuse_or_cite_old_receipts(tmp_path) -> None:
    root = tmp_path / "fixtures" / "forget-me-graph"
    seed_estate(root, selector_secret=SECRET)
    context, protector, selector_a, plan_a = _build_fixture_plan(selector_value="42")
    receipts_a = execute_plan(
        root=root,
        plan=plan_a,
        confirmation=PlanConfirmation.grant(plan_a, confirmed_by="privacy-operator"),
        selector=selector_a,
        protector=protector,
        artifacts=context.artifacts(),
        selector_secret=SECRET,
    )
    _, _, selector_b, plan_b = _build_fixture_plan(selector_value="1")

    certificate_b = verify_and_certify(
        root=root,
        plan=plan_b,
        selector=selector_b,
        protector=protector,
        artifacts=context.artifacts(),
        receipts=receipts_a,
        selector_secret=SECRET,
    )
    assert certificate_b.status is CertificateStatus.INCOMPLETE
    assert all(
        item.receipt_id is None for item in certificate_b.items if item.status is ItemStatus.FAILED
    )

    receipts_b = execute_plan(
        root=root,
        plan=plan_b,
        confirmation=PlanConfirmation.grant(plan_b, confirmed_by="privacy-operator"),
        selector=selector_b,
        protector=protector,
        artifacts=context.artifacts(),
        selector_secret=SECRET,
    )
    assert len(receipts_b) == 9
    assert {receipt.receipt_id for receipt in receipts_a}.isdisjoint(
        receipt.receipt_id for receipt in receipts_b
    )
    assert all(
        receipt.idempotency_key
        == execution_idempotency_key(
            plan_hash=plan_b.plan_hash,
            target_urn=receipt.target_urn,
            action=receipt.action,
        )
        for receipt in receipts_b
    )
    after = inspect_presence(root, customer_id=1, selector_secret=SECRET)
    assert all(count == 0 for count in after["artifacts"].values())


def test_persisted_certificate_detects_tampering(tmp_path: Path) -> None:
    root = tmp_path / "fixtures" / "forget-me-graph"
    seed_estate(root, selector_secret=SECRET)
    context, protector, selector, plan = _build_fixture_plan()
    confirmation = PlanConfirmation.grant(plan, confirmed_by="privacy-operator")
    receipts = execute_plan(
        root=root,
        plan=plan,
        confirmation=confirmation,
        selector=selector,
        protector=protector,
        artifacts=context.artifacts(),
        selector_secret=SECRET,
    )
    verify_and_certify(
        root=root,
        plan=plan,
        selector=selector,
        protector=protector,
        artifacts=context.artifacts(),
        receipts=receipts,
        selector_secret=SECRET,
    )
    path = root / "evidence/req-execution-test/certificate.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["request_id"] = "req-tampered"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hash verification failed"):
        verify_certificate_file(path)
    assert verify_certificate_main([str(path)]) == 1


def test_certificate_refuses_complete_when_record_is_retained(tmp_path) -> None:
    root = tmp_path / "fixtures" / "forget-me-graph"
    seed_estate(root, selector_secret=SECRET)
    context, protector, selector, plan = _build_fixture_plan()
    confirmation = PlanConfirmation.grant(plan, confirmed_by="privacy-operator")
    receipts = execute_plan(
        root=root,
        plan=plan,
        confirmation=confirmation,
        selector=selector,
        protector=protector,
        artifacts=context.artifacts(),
        selector_secret=SECRET,
    )
    connection = sqlite3.connect(root / "vector_index.sqlite")
    try:
        connection.execute(
            "INSERT INTO vectors VALUES (?, ?, ?, ?, ?)",
            ("retained-test", 9999, 42, "synthetic-hash", "[]"),
        )
        connection.commit()
    finally:
        connection.close()

    certificate = verify_and_certify(
        root=root,
        plan=plan,
        selector=selector,
        protector=protector,
        artifacts=context.artifacts(),
        receipts=receipts,
        selector_secret=SECRET,
    )

    vector_item = next(
        item for item in certificate.items if item.artifact_name == "vectors.ticket_embeddings"
    )
    assert vector_item.status is ItemStatus.FAILED
    assert certificate.status is CertificateStatus.INCOMPLETE


def test_certificate_never_uses_another_requests_receipt(tmp_path) -> None:
    root = tmp_path / "fixtures" / "forget-me-graph"
    seed_estate(root, selector_secret=SECRET)
    context, protector, selector, plan = _build_fixture_plan()
    decision = next(item for item in plan.decisions if item.status.value == "ready")
    foreign_receipt = ExecutionReceipt.create(
        idempotency_key="foreign-idempotency-key",
        request_id="req-different-request",
        target_urn=decision.target_urn,
        artifact_name=next(
            artifact.name for artifact in context.artifacts() if artifact.urn == decision.target_urn
        ),
        action=decision.action,
        status=ReceiptStatus.SUCCEEDED,
        before_count=1,
        after_count=0,
        started_at=datetime.now(UTC),
        detail="foreign successful receipt",
    )

    certificate = verify_and_certify(
        root=root,
        plan=plan,
        selector=selector,
        protector=protector,
        artifacts=context.artifacts(),
        receipts=[foreign_receipt],
        selector_secret=SECRET,
    )

    item = next(value for value in certificate.items if value.target_urn == decision.target_urn)
    assert item.status is ItemStatus.FAILED
    assert item.receipt_id is None
