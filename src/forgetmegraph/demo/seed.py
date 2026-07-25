from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any

import duckdb
import joblib
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.linear_model import LogisticRegression

from forgetmegraph.domain.models import SubjectSelector
from forgetmegraph.privacy.selector import SelectorProtector

DEMO_SECRET = "forgetmegraph-demo-secret-change-me"
MARKER = ".forgetmegraph-demo"

CUSTOMERS = [
    (1, "Avery Example", "standard"),
    (2, "Blake Example", "premium"),
    (3, "Casey Example", "standard"),
    (4, "Drew Example", "premium"),
    (5, "Emery Example", "standard"),
    (42, "Synthetic Subject", "premium"),
]

TICKETS = [
    (1001, 1, "Password reset completed", "resolved", 0),
    (1002, 1, "Cannot update profile", "account", 1),
    (2001, 2, "Billing charge needs review", "billing", 1),
    (3001, 3, "Thanks for the quick help", "resolved", 0),
    (4001, 4, "Account access is blocked", "account", 1),
    (5001, 5, "Documentation question answered", "resolved", 0),
    (4201, 42, "Refund request for duplicate charge", "billing", 1),
    (4202, 42, "Follow up on account access", "account", 1),
]


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_prepare_root(root: Path) -> Path:
    root = root.resolve()
    if root.exists():
        marker = root / MARKER
        if not marker.exists():
            if any(root.iterdir()):
                raise ValueError(f"refusing to replace unmarked artifact directory: {root}")
        else:
            shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    (root / MARKER).write_text("synthetic disposable demo artifacts\n", encoding="utf-8")
    return root


def _selector_token(customer_id: int, secret: str) -> str:
    protector = SelectorProtector(secret)
    protected = protector.protect(
        SubjectSelector(subject_type="customer", field="customer_id", value=str(customer_id))
    )
    return protected.token


def seed_estate(root: Path, *, selector_secret: str = DEMO_SECRET) -> dict[str, Any]:
    root = _safe_prepare_root(root)
    database_path = root / "estate.duckdb"
    connection = duckdb.connect(str(database_path))
    try:
        connection.execute("CREATE SCHEMA raw; CREATE SCHEMA analytics; CREATE SCHEMA features;")
        connection.execute(
            "CREATE TABLE raw.customers "
            "(customer_id INTEGER PRIMARY KEY, name VARCHAR, segment VARCHAR)"
        )
        connection.executemany("INSERT INTO raw.customers VALUES (?, ?, ?)", CUSTOMERS)
        connection.execute(
            "CREATE TABLE raw.tickets "
            "(ticket_id INTEGER PRIMARY KEY, customer_id INTEGER, ticket_text VARCHAR, "
            "category VARCHAR, needs_follow_up INTEGER)"
        )
        connection.executemany("INSERT INTO raw.tickets VALUES (?, ?, ?, ?, ?)", TICKETS)
        connection.execute(
            """
            CREATE TABLE analytics.customer_ticket_summary AS
            SELECT
                c.customer_id,
                c.segment,
                COUNT(t.ticket_id)::INTEGER AS ticket_count,
                COALESCE(SUM(t.needs_follow_up), 0)::INTEGER AS follow_up_count
            FROM raw.customers c
            LEFT JOIN raw.tickets t USING (customer_id)
            GROUP BY c.customer_id, c.segment
            """
        )
        connection.execute(
            """
            CREATE TABLE features.customer_support_profile AS
            SELECT
                customer_id,
                ticket_count,
                follow_up_count,
                CASE WHEN segment = 'premium' THEN 1 ELSE 0 END AS premium_flag,
                CASE WHEN follow_up_count > 0 THEN 1 ELSE 0 END AS label
            FROM analytics.customer_ticket_summary
            """
        )
        connection.execute(
            """
            CREATE TABLE analytics.ticket_category_counts AS
            SELECT category, COUNT(*)::INTEGER AS ticket_count
            FROM raw.tickets
            GROUP BY category
            """
        )

        export_path = root / "customer_support_export.csv"
        connection.execute(
            "COPY analytics.customer_ticket_summary TO ? (HEADER, DELIMITER ',')",
            [str(export_path)],
        )
        snapshot_path = root / "training_snapshot_v1.csv"
        connection.execute(
            "COPY features.customer_support_profile TO ? (HEADER, DELIMITER ',')",
            [str(snapshot_path)],
        )

        training_rows = connection.execute(
            "SELECT customer_id, ticket_count, follow_up_count, premium_flag, label "
            "FROM features.customer_support_profile ORDER BY customer_id"
        ).fetchall()
        features = [list(row[1:4]) for row in training_rows]
        labels = [row[4] for row in training_rows]
        model = LogisticRegression(random_state=7, solver="liblinear")
        model.fit(features, labels)
        model_path = root / "model_v1.joblib"
        joblib.dump(model, model_path)
    finally:
        connection.close()

    vectorizer = HashingVectorizer(
        n_features=32,
        alternate_sign=False,
        norm="l2",
        stop_words="english",
    )
    vectors = vectorizer.transform([ticket[2] for ticket in TICKETS]).toarray()
    vector_db = sqlite3.connect(root / "vector_index.sqlite")
    try:
        vector_db.execute(
            "CREATE TABLE vectors "
            "(record_id TEXT PRIMARY KEY, ticket_id INTEGER, customer_id INTEGER, "
            "content_sha256 TEXT, vector_json TEXT)"
        )
        vector_db.executemany(
            "INSERT INTO vectors VALUES (?, ?, ?, ?, ?)",
            [
                (
                    f"ticket-{ticket[0]}",
                    ticket[0],
                    ticket[1],
                    sha256(ticket[2].encode("utf-8")).hexdigest(),
                    json.dumps(vector.tolist(), separators=(",", ":")),
                )
                for ticket, vector in zip(TICKETS, vectors, strict=True)
            ],
        )
        vector_db.commit()
    finally:
        vector_db.close()

    cache_db = sqlite3.connect(root / "cache.sqlite")
    try:
        cache_db.execute(
            "CREATE TABLE cache_entries "
            "(cache_key TEXT PRIMARY KEY, subject_token TEXT, value_json TEXT)"
        )
        cache_db.executemany(
            "INSERT INTO cache_entries VALUES (?, ?, ?)",
            [
                (
                    f"summary:{_selector_token(customer_id, selector_secret)}",
                    _selector_token(customer_id, selector_secret),
                    json.dumps(
                        {
                            "ticket_count": ticket_count,
                            "follow_up_count": follow_up_count,
                        },
                        sort_keys=True,
                    ),
                )
                for customer_id, _, ticket_count, follow_up_count in _read_export(export_path)
            ],
        )
        cache_db.commit()
    finally:
        cache_db.close()

    subject_tokens = [_selector_token(int(row[0]), selector_secret) for row in training_rows]
    manifest = {
        "model_version": "model-v1",
        "model_kind": "sklearn_logistic_regression",
        "training_snapshot": snapshot_path.name,
        "training_snapshot_sha256": _sha256_file(snapshot_path),
        "model_file": model_path.name,
        "model_sha256": _sha256_file(model_path),
        "subject_tokens": subject_tokens,
        "claim": "clean training snapshot and full retraining; not formal unlearning",
        "active": True,
    }
    (root / "active_model_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    result = inspect_presence(root, customer_id=42, selector_secret=selector_secret)
    (root / "before_presence.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def _read_export(path: Path) -> list[tuple[int, str, int, int]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            (
                int(row["customer_id"]),
                row["segment"],
                int(row["ticket_count"]),
                int(row["follow_up_count"]),
            )
            for row in csv.DictReader(handle)
        ]


def inspect_presence(
    root: Path, *, customer_id: int, selector_secret: str = DEMO_SECRET
) -> dict[str, Any]:
    root = root.resolve()
    token = _selector_token(customer_id, selector_secret)
    connection = duckdb.connect(str(root / "estate.duckdb"), read_only=True)
    try:
        counts = {
            "raw.customers": connection.execute(
                "SELECT COUNT(*) FROM raw.customers WHERE customer_id = ?", [customer_id]
            ).fetchone()[0],
            "raw.tickets": connection.execute(
                "SELECT COUNT(*) FROM raw.tickets WHERE customer_id = ?", [customer_id]
            ).fetchone()[0],
            "analytics.customer_ticket_summary": connection.execute(
                "SELECT COUNT(*) FROM analytics.customer_ticket_summary WHERE customer_id = ?",
                [customer_id],
            ).fetchone()[0],
            "features.customer_support_profile": connection.execute(
                "SELECT COUNT(*) FROM features.customer_support_profile WHERE customer_id = ?",
                [customer_id],
            ).fetchone()[0],
        }
    finally:
        connection.close()

    vector_db = sqlite3.connect(root / "vector_index.sqlite")
    try:
        counts["vectors.ticket_embeddings"] = vector_db.execute(
            "SELECT COUNT(*) FROM vectors WHERE customer_id = ?", (customer_id,)
        ).fetchone()[0]
    finally:
        vector_db.close()

    cache_db = sqlite3.connect(root / "cache.sqlite")
    try:
        counts["cache.customer_summary"] = cache_db.execute(
            "SELECT COUNT(*) FROM cache_entries WHERE subject_token = ?", (token,)
        ).fetchone()[0]
    finally:
        cache_db.close()

    counts["exports.customer_support.csv"] = sum(
        1 for row in _read_export(root / "customer_support_export.csv") if row[0] == customer_id
    )
    manifest = json.loads((root / "active_model_manifest.json").read_text(encoding="utf-8"))
    active_snapshot = root / manifest["training_snapshot"]
    with active_snapshot.open(newline="", encoding="utf-8") as handle:
        counts["training.customer_support.v1"] = sum(
            1 for row in csv.DictReader(handle) if int(row["customer_id"]) == customer_id
        )
    counts["model.customer_support_classifier"] = int(token in manifest["subject_tokens"])

    return {
        "selector_token": token,
        "artifacts": counts,
        "aggregate_exemption": {
            "artifact": "analytics.ticket_category_counts",
            "status": "exempt",
            "reason": "Aggregate contains category counts and no subject-addressable key.",
        },
    }


def _default_root() -> Path:
    return Path(
        os.getenv(
            "DEMO_FIXTURE_ROOT",
            "demo/fixtures/forget-me-graph",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the synthetic Forget-Me-Graph estate")
    parser.add_argument("command", choices=["seed", "reset", "presence"], nargs="?", default="seed")
    parser.add_argument("--root", type=Path, default=_default_root())
    parser.add_argument("--customer-id", type=int, default=42)
    args = parser.parse_args()

    if args.command in {"seed", "reset"}:
        output = seed_estate(args.root)
    else:
        output = inspect_presence(args.root, customer_id=args.customer_id)
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
