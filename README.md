# Forget-Me-Graph

![Forget-Me-Graph — Trace. Execute. Verify.](docs/assets/forget-me-graph-social-card.png)

**A DataHub-powered deletion and clean-retraining orchestrator with verifiable evidence.**

A source deletion does not remove the same subject from derived tables, feature data, vector
indexes, caches, exports, training snapshots, or learned artifacts. Forget-Me-Graph turns a scoped
synthetic request into an exact lineage impact plan, requires approval for the immutable plan hash,
executes real disposable mutations, independently verifies every reachable artifact, and writes a
receipt-backed result to DataHub.

The result is deliberately precise: the demo finishes as `verified_with_limitations` because one
aggregate has no subject-addressable key. Clean-snapshot retraining is demonstrated; universal or
mathematical machine unlearning is not claimed.

## Judge journey

The same-origin evidence console presents the complete workflow:

1. Enter a masked synthetic selector at the privacy boundary.
2. Inspect the exact 10-asset, 9-edge DataHub impact graph and selector mappings.
3. Review deterministic purge, rebuild, vector deletion, eviction, replacement, retraining, and
   exemption decisions.
4. Approve the exact SHA-256 plan hash.
5. Watch guarded adapters mutate the marked disposable fixture.
6. Inspect independently queried before/after results.
7. Download JSON/Markdown certificates and, in live mode, DataHub read and write/reread receipts.

The UI does not simulate a second workflow: it calls the same planner, executor, verifier, and
DataHub integration used by the command-line demo.

## What is real

- Live open-source DataHub MCP `get_entities` and downstream `get_lineage` calls gate every planned
  target.
- DuckDB row purge and derived/feature rebuilds execute against a marked synthetic fixture.
- Vector records, cache entries, CSV exports, and training snapshots are deleted or rebuilt.
- A scikit-learn classifier is fully retrained from the clean snapshot; the old manifest is retired
  and the active pointer is switched.
- Verification re-queries stores instead of trusting adapter success messages.
- A supported DataHub SDK patch writes five allowlisted evidence properties to one allowlisted
  dataset and immediately rereads them for exact equality.
- Readiness is non-mutating and fails closed unless the local marker, exact active DataHub catalog,
  complete lineage, and required MCP capabilities are current.

## Safety boundary

- Synthetic data only; do not use real personal information.
- Raw selector values are intake-only, marked `repr=False`, omitted from plans/responses/evidence,
  and cleared from the visible form after planning.
- Request validation errors are generic so rejected values are not echoed.
- Destructive execution requires explicit approval bound to the current deterministic plan hash.
- The synthetic fixture marker, exact `forgetme.` namespace, fixed target allowlists, and explicit
  selector mappings are checked before mutation.
- Live environments force the DataHub read/write gate even if a client asks for local mode.
- Evidence downloads use an exact filename allowlist and validated request IDs.

See [Privacy Boundary](docs/PRIVACY.md), [Defensible Claims](docs/CLAIMS.md), and
[Limitations](docs/LIMITATIONS.md).

## Run locally

Requirements: Python 3.12+.

```powershell
python -m pip install -e ".[dev,datahub]"
python -m forgetmegraph.demo.seed seed
python -m forgetmegraph.api
```

Open `http://127.0.0.1:8103`. Local API mode can exercise the real disposable adapters without
DataHub by clearing **Require live DataHub read/write** in the approval card. The result honestly
labels DataHub context and writeback as not required; it does not produce DataHub receipts.

Command-line equivalent:

```powershell
python -m forgetmegraph.demo.workflow --approved-by demo-privacy-operator --seed
```

## Run the live DataHub path

Use a dedicated service-account token supplied out of band. Never echo it, place it on a command
line, or commit it.

```powershell
$env:DATAHUB_GMS_URL = 'http://127.0.0.1:8080'
$env:DATAHUB_MCP_URL = 'http://127.0.0.1:8000/mcp'
$env:DATAHUB_URN_PREFIX = 'forgetme.'
python -m forgetmegraph.demo.datahub_catalog seed-datahub
python -m forgetmegraph.demo.workflow --approved-by demo-privacy-operator --seed --require-datahub
```

Catalog lifecycle operations are narrow and reversible:

```powershell
python -m forgetmegraph.demo.datahub_catalog reset-datahub
python -m forgetmegraph.demo.datahub_catalog restore-datahub
```

`reset-datahub` soft-deletes exactly the ten allowlisted datasets; it is not a hard delete.
`restore-datahub` reactivates the same set and rereads metadata plus all nine edges. Both reject
foreign, extra, partial, or empty target sets before emission.

## Verify

```powershell
python -m ruff check src tests
python -m pytest --cov=forgetmegraph --cov-report=term-missing -q
node --check src/forgetmegraph/ui/app.js
```

The test suite covers selector propagation, missing mappings, approval/plan binding, fixture and
namespace guards, idempotency, real adapters, retained-record failures, retraining, certificate
accuracy, live-context fail-closed behavior, catalog seed/reset/restore isolation, readiness drift,
UI redaction, and evidence-download allowlists.

## Coordinator-verified live proof

The deployed backend candidate `8a24421f99622140bfa3e75c8db7ec3923f100de` passed:

- exact seed of 10 active datasets and 9 lineage edges;
- approved workflow with `verified_with_limitations`;
- MCP read receipt and supported SDK write with immediate exact reread;
- readiness transition `200 restored -> 503 reset -> 200 restored`;
- soft reset preserving 102 foreign Lifeboat aspect rows byte-for-byte;
- a simultaneous isolated run using separate private pinned MCP workers; and
- a read-only snapshot whose certificate hash matched exactly.

Public-safe hashes are in [live-evidence-summary.json](examples/live-evidence-summary.json).
Coordinator provenance and exact operational commands remain in
[COORDINATOR_HANDOFF.md](COORDINATOR_HANDOFF.md). Runtime receipts, selectors, credentials, and raw
MCP responses are intentionally not committed.

## Repository map

- `src/forgetmegraph/ui/` — judge-facing evidence console
- `src/forgetmegraph/context/` — live DataHub MCP/GMS integration and receipts
- `src/forgetmegraph/planning/` — deterministic lineage traversal, mappings, and policy
- `src/forgetmegraph/execution/` — allowlisted purge/rebuild/retrain adapters
- `src/forgetmegraph/verification/` — independent verification and certificates
- `demo/metadata/graph.json` — exact executable 10-node fixture
- `demo/selector-mappings.json` — versioned selector propagation metadata
- `examples/` — redacted non-runtime examples and coordinator-owned public hashes
- `docs/DEMO_RECORDING.md` — under-three-minute recording runbook
- `SUBMISSION.md` — Devpost-ready copy and final placeholders

## Submission facts

- Category: **Production ML Agents**, with **Agents That Do Real Work** as a secondary fit.
- License: [Apache 2.0](LICENSE).
- Built during the hackathon submission period; no meaningful pre-existing product code is
  incorporated.
- Uses synthetic customer-support data generated by this repository.
- Uses open-source DataHub plus the DataHub MCP server and supported Python SDK writeback.

Forget-Me-Graph is the graph-aware orchestration and evidence layer. It is not legal advice, a
catalog completeness guarantee, or a universal machine-unlearning algorithm.
