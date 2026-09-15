from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256
from hmac import compare_digest
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from forgetmegraph.demo.seed import inspect_presence
from forgetmegraph.domain.models import (
    ActionPlan,
    Artifact,
    DecisionStatus,
    ProtectedSelector,
)
from forgetmegraph.execution.models import (
    ExecutionReceipt,
    ReceiptStatus,
    execution_idempotency_key,
)
from forgetmegraph.execution.safety import require_fixture_marker
from forgetmegraph.privacy.selector import SelectorProtector


class ItemStatus(StrEnum):
    VERIFIED = "verified"
    FAILED = "failed"
    BLOCKED = "blocked"
    EXEMPT = "exempt"
    OUT_OF_SCOPE = "out_of_scope"


class CertificateStatus(StrEnum):
    VERIFIED = "verified"
    VERIFIED_WITH_LIMITATIONS = "verified_with_limitations"
    INCOMPLETE = "incomplete"


class CertificateItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_urn: str
    artifact_name: str
    action: str
    status: ItemStatus
    before_count: int | None
    after_count: int | None
    receipt_id: str | None
    limitation: str | None


class EvidenceCertificate(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    selector_token: str
    plan_hash: str
    generated_at: datetime
    status: CertificateStatus
    items: list[CertificateItem]
    datahub_read_receipt_sha256: str | None = None
    certificate_hash: str


def _aggregate_status(items: list[CertificateItem]) -> CertificateStatus:
    statuses = {item.status for item in items}
    if ItemStatus.FAILED in statuses or ItemStatus.BLOCKED in statuses:
        return CertificateStatus.INCOMPLETE
    if ItemStatus.EXEMPT in statuses or ItemStatus.OUT_OF_SCOPE in statuses:
        return CertificateStatus.VERIFIED_WITH_LIMITATIONS
    return CertificateStatus.VERIFIED


def _canonical_datetime(value: datetime) -> str:
    normalized = value.astimezone(UTC)
    return normalized.isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_certificate_payload(certificate: EvidenceCertificate) -> bytes:
    """Return the versioned bytes covered by ``certificate_hash``."""

    payload = certificate.model_dump(mode="json", exclude={"certificate_hash"})
    if certificate.datahub_read_receipt_sha256 is None:
        payload.pop("datahub_read_receipt_sha256", None)
    payload["generated_at"] = _canonical_datetime(certificate.generated_at)
    hash_schema = (
        "forgetme-certificate-v2"
        if certificate.datahub_read_receipt_sha256 is not None
        else "forgetme-certificate-v1"
    )
    envelope = {"hash_schema": hash_schema, "certificate": payload}
    return json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode("utf-8")


def compute_certificate_hash(certificate: EvidenceCertificate) -> str:
    return sha256(canonical_certificate_payload(certificate)).hexdigest()


def verify_certificate(certificate: EvidenceCertificate) -> bool:
    """Recompute and compare the embedded certificate hash."""

    return compare_digest(certificate.certificate_hash, compute_certificate_hash(certificate))


def verify_certificate_file(path: Path) -> EvidenceCertificate:
    """Verify a certificate and any adjacent DataHub read receipt it references."""

    certificate = EvidenceCertificate.model_validate_json(path.read_text(encoding="utf-8"))
    if not verify_certificate(certificate):
        raise ValueError("certificate hash verification failed")
    if certificate.datahub_read_receipt_sha256 is not None:
        from forgetmegraph.context.datahub import DataHubReadReceipt

        receipt_path = path.with_name("datahub-read-receipt.json")
        receipt = DataHubReadReceipt.model_validate_json(receipt_path.read_text(encoding="utf-8"))
        if not receipt.verifies_binding(
            request_id=certificate.request_id,
            plan_hash=certificate.plan_hash,
            receipt_sha256=certificate.datahub_read_receipt_sha256,
        ):
            raise ValueError("DataHub read receipt binding verification failed")
    return certificate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify a persisted Forget-Me-Graph evidence certificate."
    )
    parser.add_argument("certificate", type=Path)
    args = parser.parse_args(argv)
    try:
        certificate = verify_certificate_file(args.certificate)
    except (OSError, ValueError) as exc:
        print(f"certificate_invalid: {exc}", file=sys.stderr)
        return 1
    print(f"certificate_verified sha256={certificate.certificate_hash}")
    return 0


def _write_markdown(path: Path, certificate: EvidenceCertificate) -> None:
    lines = [
        "# Forget-Me-Graph Evidence Certificate",
        "",
        f"- Request: `{certificate.request_id}`",
        f"- Subject token: `{certificate.selector_token}`",
        f"- Result: **{certificate.status.value}**",
        f"- Plan hash: `{certificate.plan_hash}`",
        f"- Certificate hash: `{certificate.certificate_hash}`",
        "",
        "| Artifact | Action | Before | After | Status | Limitation |",
        "|---|---|---:|---:|---|---|",
    ]
    if certificate.datahub_read_receipt_sha256 is not None:
        lines.insert(
            7,
            f"- DataHub read receipt hash: `{certificate.datahub_read_receipt_sha256}`",
        )
    for item in certificate.items:
        before = "—" if item.before_count is None else str(item.before_count)
        after = "—" if item.after_count is None else str(item.after_count)
        limitation = item.limitation or ""
        lines.append(
            f"| `{item.artifact_name}` | {item.action} | {before} | {after} | "
            f"{item.status.value} | {limitation} |"
        )
    lines.extend(
        [
            "",
            "The model result proves a clean snapshot and full toy-model retraining. ",
            "It is not a claim of mathematical or universal machine unlearning.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def verify_and_certify(
    *,
    root: Path,
    plan: ActionPlan,
    selector: ProtectedSelector,
    protector: SelectorProtector,
    artifacts: Iterable[Artifact],
    receipts: Iterable[ExecutionReceipt],
    selector_secret: str,
    datahub_read_receipt_sha256: str | None = None,
) -> EvidenceCertificate:
    root = require_fixture_marker(root)
    revealed = protector.reveal(selector)
    customer_id = int(revealed.value)
    presence = inspect_presence(root, customer_id=customer_id, selector_secret=selector_secret)
    artifact_by_urn = {artifact.urn: artifact for artifact in artifacts}
    expected_receipt_keys = {
        (decision.target_urn, decision.action): execution_idempotency_key(
            plan_hash=plan.plan_hash,
            target_urn=decision.target_urn,
            action=decision.action,
        )
        for decision in plan.decisions
        if decision.status is DecisionStatus.READY
    }
    receipt_by_urn = {
        receipt.target_urn: receipt
        for receipt in receipts
        if receipt.request_id == plan.request_id
        and receipt.idempotency_key
        == expected_receipt_keys.get((receipt.target_urn, receipt.action))
    }
    items: list[CertificateItem] = []
    for decision in plan.decisions:
        artifact = artifact_by_urn[decision.target_urn]
        receipt = receipt_by_urn.get(decision.target_urn)
        after_count = presence["artifacts"].get(artifact.name)
        limitation: str | None = None
        if decision.status is DecisionStatus.BLOCKED:
            item_status = ItemStatus.BLOCKED
            limitation = decision.reason
        elif decision.status is DecisionStatus.EXEMPT:
            item_status = ItemStatus.EXEMPT
            limitation = decision.reason
        elif decision.status is DecisionStatus.OUT_OF_SCOPE:
            item_status = ItemStatus.OUT_OF_SCOPE
            limitation = decision.reason
        elif receipt is None or receipt.status is ReceiptStatus.FAILED:
            item_status = ItemStatus.FAILED
            limitation = "No successful execution receipt exists."
        elif after_count == 0:
            item_status = ItemStatus.VERIFIED
        else:
            item_status = ItemStatus.FAILED
            limitation = "Independent verification still found subject-addressable evidence."
        if artifact.artifact_type.value == "ml_model" and item_status is ItemStatus.VERIFIED:
            limitation = (
                "Verified active clean-snapshot retraining; not mathematical proof of forgetting."
            )
        elif artifact.artifact_type.value == "ml_model":
            limitation = (
                limitation + " " if limitation else ""
            ) + "Clean-snapshot retraining was not independently verified."
        items.append(
            CertificateItem(
                target_urn=decision.target_urn,
                artifact_name=artifact.name,
                action=decision.action.value,
                status=item_status,
                before_count=receipt.before_count if receipt else None,
                after_count=after_count,
                receipt_id=receipt.receipt_id if receipt else None,
                limitation=limitation,
            )
        )
    generated_at = datetime.now(UTC)
    unhashed = EvidenceCertificate(
        request_id=plan.request_id,
        selector_token=selector.token,
        plan_hash=plan.plan_hash,
        generated_at=generated_at,
        status=_aggregate_status(items),
        items=items,
        datahub_read_receipt_sha256=datahub_read_receipt_sha256,
        certificate_hash="0" * 64,
    )
    certificate = unhashed.model_copy(
        update={"certificate_hash": compute_certificate_hash(unhashed)}
    )
    evidence_dir = root / "evidence" / plan.request_id
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "certificate.json").write_text(
        certificate.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    verify_certificate_file(evidence_dir / "certificate.json")
    _write_markdown(evidence_dir / "certificate.md", certificate)
    return certificate


if __name__ == "__main__":
    raise SystemExit(main())
