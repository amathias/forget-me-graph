from __future__ import annotations

import json
from datetime import UTC, datetime
from enum import StrEnum
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field

from forgetmegraph.domain.models import ActionPlan, ActionType


class ReceiptStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class Approval(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    plan_hash: str
    approver: str = Field(min_length=1, max_length=200)
    approved_at: datetime

    @classmethod
    def grant(cls, plan: ActionPlan, *, approver: str) -> Approval:
        return cls(
            request_id=plan.request_id,
            plan_hash=plan.plan_hash,
            approver=approver,
            approved_at=datetime.now(UTC),
        )


class ExecutionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str
    idempotency_key: str
    request_id: str
    target_urn: str
    artifact_name: str
    action: ActionType
    status: ReceiptStatus
    before_count: int | None
    after_count: int | None
    started_at: datetime
    finished_at: datetime
    detail: str
    evidence_hash: str

    @classmethod
    def create(
        cls,
        *,
        idempotency_key: str,
        request_id: str,
        target_urn: str,
        artifact_name: str,
        action: ActionType,
        status: ReceiptStatus,
        before_count: int | None,
        after_count: int | None,
        started_at: datetime,
        detail: str,
    ) -> ExecutionReceipt:
        finished_at = datetime.now(UTC)
        payload = {
            "idempotency_key": idempotency_key,
            "request_id": request_id,
            "target_urn": target_urn,
            "artifact_name": artifact_name,
            "action": action.value,
            "status": status.value,
            "before_count": before_count,
            "after_count": after_count,
            "started_at": started_at.isoformat(),
            "finished_at": finished_at.isoformat(),
            "detail": detail,
        }
        evidence_hash = sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(
            receipt_id=f"receipt_{evidence_hash[:16]}",
            evidence_hash=evidence_hash,
            **payload,
        )
