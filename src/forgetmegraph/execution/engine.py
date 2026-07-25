from __future__ import annotations

import csv
import json
import os
import sqlite3
from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import duckdb
import joblib
from sklearn.linear_model import LogisticRegression

from forgetmegraph.demo.seed import inspect_presence
from forgetmegraph.domain.models import (
    ActionPlan,
    ActionType,
    Artifact,
    ArtifactDecision,
    DecisionStatus,
    ProtectedSelector,
    SubjectSelector,
)
from forgetmegraph.execution.models import Approval, ExecutionReceipt, ReceiptStatus
from forgetmegraph.execution.safety import (
    require_approval,
    require_fixture_marker,
    require_namespace,
)
from forgetmegraph.privacy.selector import SelectorProtector


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _receipt_path(root: Path) -> Path:
    return root / "execution_receipts.json"


def _load_receipts(root: Path) -> list[ExecutionReceipt]:
    path = _receipt_path(root)
    if not path.exists():
        return []
    return [
        ExecutionReceipt.model_validate(item)
        for item in json.loads(path.read_text(encoding="utf-8"))
    ]


def _write_receipts(root: Path, receipts: list[ExecutionReceipt]) -> None:
    path = _receipt_path(root)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            [item.model_dump(mode="json") for item in receipts],
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _presence_count(root: Path, customer_id: int, secret: str, name: str) -> int | None:
    evidence = inspect_presence(root, customer_id=customer_id, selector_secret=secret)
    return evidence["artifacts"].get(name)


def _rebuild_summary(root: Path) -> None:
    connection = duckdb.connect(str(root / "estate.duckdb"))
    try:
        connection.execute(
            """
            CREATE OR REPLACE TABLE analytics.customer_ticket_summary AS
            SELECT c.customer_id, c.segment,
                COUNT(t.ticket_id)::INTEGER AS ticket_count,
                COALESCE(SUM(t.needs_follow_up), 0)::INTEGER AS follow_up_count
            FROM raw.customers c
            LEFT JOIN raw.tickets t USING (customer_id)
            GROUP BY c.customer_id, c.segment
            """
        )
    finally:
        connection.close()


def _rebuild_features(root: Path) -> None:
    connection = duckdb.connect(str(root / "estate.duckdb"))
    try:
        connection.execute(
            """
            CREATE OR REPLACE TABLE features.customer_support_profile AS
            SELECT customer_id, ticket_count, follow_up_count,
                CASE WHEN segment = 'premium' THEN 1 ELSE 0 END AS premium_flag,
                CASE WHEN follow_up_count > 0 THEN 1 ELSE 0 END AS label
            FROM analytics.customer_ticket_summary
            """
        )
    finally:
        connection.close()


def _purge_rows(root: Path, table: str, customer_id: int) -> None:
    if table not in {"raw.customers", "raw.tickets"}:
        raise ValueError("row purge target is not allowlisted")
    connection = duckdb.connect(str(root / "estate.duckdb"))
    try:
        connection.execute(f"DELETE FROM {table} WHERE customer_id = ?", [customer_id])
    finally:
        connection.close()


def _delete_vectors(root: Path, customer_id: int) -> None:
    connection = sqlite3.connect(root / "vector_index.sqlite")
    try:
        connection.execute("DELETE FROM vectors WHERE customer_id = ?", (customer_id,))
        connection.commit()
    finally:
        connection.close()


def _evict_cache(root: Path, selector_token: str) -> None:
    connection = sqlite3.connect(root / "cache.sqlite")
    try:
        connection.execute("DELETE FROM cache_entries WHERE subject_token = ?", (selector_token,))
        connection.commit()
    finally:
        connection.close()


def _copy_query(root: Path, query: str, destination: Path) -> None:
    temporary = destination.with_suffix(".next.csv")
    if temporary.exists():
        temporary.unlink()
    connection = duckdb.connect(str(root / "estate.duckdb"), read_only=True)
    try:
        connection.execute(f"COPY ({query}) TO ? (HEADER, DELIMITER ',')", [str(temporary)])
    finally:
        connection.close()
    os.replace(temporary, destination)


def _retrain_model(root: Path, protector: SelectorProtector) -> None:
    snapshot = root / "training_snapshot_v2.csv"
    with snapshot.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    features = [
        [int(row["ticket_count"]), int(row["follow_up_count"]), int(row["premium_flag"])]
        for row in rows
    ]
    labels = [int(row["label"]) for row in rows]
    model = LogisticRegression(random_state=7, solver="liblinear")
    model.fit(features, labels)
    model_path = root / "model_v2.joblib"
    joblib.dump(model, model_path)
    active_path = root / "active_model_manifest.json"
    previous = json.loads(active_path.read_text(encoding="utf-8"))
    previous["active"] = False
    (root / f"retired_{previous['model_version']}_manifest.json").write_text(
        json.dumps(previous, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    subject_tokens = [
        protector.protect(
            SubjectSelector(subject_type="customer", field="customer_id", value=row["customer_id"])
        ).token
        for row in rows
    ]
    manifest = {
        "model_version": "model-v2",
        "model_kind": "sklearn_logistic_regression",
        "training_snapshot": snapshot.name,
        "training_snapshot_sha256": _file_hash(snapshot),
        "model_file": model_path.name,
        "model_sha256": _file_hash(model_path),
        "subject_tokens": subject_tokens,
        "supersedes": previous["model_version"],
        "claim": "clean training snapshot and full retraining; not formal unlearning",
        "active": True,
    }
    temporary = active_path.with_suffix(".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, active_path)


def _execute_decision(
    root: Path,
    decision: ArtifactDecision,
    artifact: Artifact,
    *,
    customer_id: int,
    selector_token: str,
    protector: SelectorProtector,
) -> None:
    if decision.action is ActionType.ROW_PURGE:
        _purge_rows(root, artifact.name, customer_id)
    elif decision.action is ActionType.REBUILD:
        if artifact.name == "analytics.customer_ticket_summary":
            _rebuild_summary(root)
        elif artifact.name == "features.customer_support_profile":
            _rebuild_features(root)
        elif artifact.name == "training.customer_support.v1":
            _copy_query(
                root,
                "SELECT * FROM features.customer_support_profile",
                root / "training_snapshot_v2.csv",
            )
        else:
            raise ValueError("rebuild target is not allowlisted")
    elif decision.action is ActionType.VECTOR_DELETE_REINDEX:
        _delete_vectors(root, customer_id)
    elif decision.action is ActionType.CACHE_EVICT:
        _evict_cache(root, selector_token)
    elif decision.action is ActionType.EXPORT_REPLACE:
        _copy_query(
            root,
            "SELECT * FROM analytics.customer_ticket_summary",
            root / "customer_support_export.csv",
        )
    elif decision.action is ActionType.RETRAIN:
        _retrain_model(root, protector)
    else:
        raise ValueError("action is not executable by the local adapter set")


def execute_plan(
    *,
    root: Path,
    plan: ActionPlan,
    approval: Approval,
    selector: ProtectedSelector,
    protector: SelectorProtector,
    artifacts: Iterable[Artifact],
    selector_secret: str,
    namespace_prefix: str = "forgetme.",
) -> list[ExecutionReceipt]:
    require_approval(plan, approval)
    root = require_fixture_marker(root)
    require_namespace(plan, namespace_prefix)
    (root / "approval.json").write_text(
        approval.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    revealed = protector.reveal(selector)
    if revealed.field != "customer_id" or revealed.operator.value != "equals":
        raise ValueError("the local demo adapter supports only customer_id equality")
    customer_id = int(revealed.value)
    artifact_by_urn = {artifact.urn: artifact for artifact in artifacts}
    receipts = _load_receipts(root)
    succeeded = {
        item.idempotency_key for item in receipts if item.status is ReceiptStatus.SUCCEEDED
    }
    ordered = sorted(plan.decisions, key=lambda item: (len(item.lineage_path), item.target_urn))
    for decision in ordered:
        if decision.status is not DecisionStatus.READY:
            continue
        artifact = artifact_by_urn[decision.target_urn]
        idempotency_key = sha256(
            f"{plan.plan_hash}:{decision.target_urn}:{decision.action.value}".encode()
        ).hexdigest()
        if idempotency_key in succeeded:
            continue
        started_at = datetime.now(UTC)
        before_count = _presence_count(root, customer_id, selector_secret, artifact.name)
        try:
            _execute_decision(
                root,
                decision,
                artifact,
                customer_id=customer_id,
                selector_token=selector.token,
                protector=protector,
            )
            after_count = _presence_count(root, customer_id, selector_secret, artifact.name)
            receipt = ExecutionReceipt.create(
                idempotency_key=idempotency_key,
                request_id=plan.request_id,
                target_urn=decision.target_urn,
                artifact_name=artifact.name,
                action=decision.action,
                status=ReceiptStatus.SUCCEEDED,
                before_count=before_count,
                after_count=after_count,
                started_at=started_at,
                detail="approved local adapter action completed",
            )
        except Exception:
            receipt = ExecutionReceipt.create(
                idempotency_key=idempotency_key,
                request_id=plan.request_id,
                target_urn=decision.target_urn,
                artifact_name=artifact.name,
                action=decision.action,
                status=ReceiptStatus.FAILED,
                before_count=before_count,
                after_count=None,
                started_at=started_at,
                detail="local adapter action failed; raw exception was not persisted",
            )
            receipts.append(receipt)
            _write_receipts(root, receipts)
            break
        receipts.append(receipt)
        succeeded.add(idempotency_key)
        _write_receipts(root, receipts)
    return receipts
