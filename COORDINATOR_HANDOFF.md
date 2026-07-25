# Coordinator Handoff: Forget-Me-Graph

## Relationship to the portfolio coordinator

This project chat owns Forget-Me-Graph product code, tests, demo evidence, and submission material.
The coordinator at `../COORDINATOR_PLAN.md` owns shared DataHub and AWS deployment. This project did
not deploy, access EC2, request a token value, or modify another workspace.

## Fixed project allocation

| Setting | Value |
|---|---|
| Project slug | `forget-me-graph` |
| Internal port | `8103` |
| DataHub domain | `Demo / Forget-Me-Graph` |
| Required DataHub tag | `project-forget-me-graph` |
| Entity prefix | `forgetme.` |
| Fixture root | `demo/fixtures/forget-me-graph` |
| State root | `/var/lib/datahub-hackathon/forget-me-graph` |

## Milestone handoff

| Field | Current value |
|---|---|
| Status | Code and local verification complete; coordinator live promotion/evidence required |
| Milestone | Exact DataHub catalog seed, guarded soft reset/restore, live lineage gate, and verified evidence writeback |
| Prior deployed commit | `477604258142f460bc1946b56f9c685d3cd9e61b` |
| Prior live result | Health 200 and readiness 200; workflow failed closed in `read_context` because lineage was incomplete; no deletion or DataHub write receipt occurred |
| New clean commit | Reported by `git rev-parse HEAD` after this handoff is committed |
| Build command | `python -m pip install -e ".[dev,datahub]"` |
| Test command | `python -m ruff check src tests; python -m pytest --cov=forgetmegraph --cov-report=term-missing -q` |
| Test evidence | 27 passing tests, 88% total coverage, Ruff clean |
| Local demo result | `verified_with_limitations` because the subject-unaddressable aggregate is explicitly exempt |
| Live evidence | Not claimed by this workspace; coordinator must capture the sequence below after promotion |

## Exact tunnel, configuration, and live sequence

Open the coordinator-owned tunnels from this workspace in separate PowerShell terminals:

```powershell
powershell -ExecutionPolicy Bypass -File ..\infra\scripts\open_tunnel.ps1 -Service gms
powershell -ExecutionPolicy Bypass -File ..\infra\scripts\open_tunnel.ps1 -Service mcp
```

In the application terminal, obtain `DATAHUB_TOKEN` only through the coordinator's existing secret
mechanism. Do not echo it, pass it on the command line, or save it in a project file.

```powershell
$env:DATAHUB_GMS_URL = 'http://127.0.0.1:8080'
$env:DATAHUB_MCP_URL = 'http://127.0.0.1:8000/mcp'
$env:DATAHUB_URN_PREFIX = 'forgetme.'
$env:DATAHUB_PROBE_URN = 'urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)'
python -m pip install -e ".[dev,datahub]"
python -m ruff check src tests
python -m pytest --cov=forgetmegraph --cov-report=term-missing -q
python -m forgetmegraph.demo.datahub_catalog seed-datahub
python -m forgetmegraph.demo.workflow --approved-by demo-privacy-operator --seed --require-datahub
python -m forgetmegraph.demo.datahub_catalog reset-datahub
python -m forgetmegraph.demo.datahub_catalog restore-datahub
```

The command is also installed as `forgetmegraph-datahub`, with the same three operation names.
Run reset and restore only after saving the workflow read/write receipts. `reset-datahub` is a
confirmed soft reset, not a hard delete; `restore-datahub` immediately proves all ten datasets are
visible and all required metadata and lineage remain intact.

Start the API and perform non-mutating endpoint checks separately:

```powershell
python -m forgetmegraph.api
Invoke-RestMethod http://127.0.0.1:8103/api/health
Invoke-RestMethod http://127.0.0.1:8103/api/readiness
```

## Exact catalog fixture and namespace guard

The lifecycle command reads `demo/metadata/graph.json` and refuses to emit unless the fixture is
exactly these ten dataset URNs. A foreign namespace, extra target, partial target set, empty target
set, metadata drift, duplicate, endpoint outside the fixture, or edge drift fails before emission.

1. `urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)`
2. `urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.tickets,PROD)`
3. `urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.analytics.customer_ticket_summary,PROD)`
4. `urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.features.customer_support_profile,PROD)`
5. `urn:li:dataset:(urn:li:dataPlatform:vector,forgetme.ticket_embeddings,PROD)`
6. `urn:li:dataset:(urn:li:dataPlatform:cache,forgetme.customer_summary_cache,PROD)`
7. `urn:li:dataset:(urn:li:dataPlatform:file,forgetme.customer_support_export,PROD)`
8. `urn:li:dataset:(urn:li:dataPlatform:file,forgetme.training_snapshot.v1,PROD)`
9. `urn:li:dataset:(urn:li:dataPlatform:mlflow,forgetme.model.customer_support_classifier,PROD)`
10. `urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.analytics.ticket_category_counts,PROD)`

All nodes are dataset URNs so every one of the nine edges uses DataHub's supported dataset-lineage
API. The feature table and model still carry the exact `feature_table` and `ml_model` artifact types
in fixture metadata and `datasetProperties.customProperties`, so planner and adapter semantics are
unchanged.

Exact transformed edges:

1. raw customers -> customer ticket summary
2. raw tickets -> customer ticket summary
3. raw tickets -> ticket embeddings
4. raw tickets -> ticket category counts
5. customer ticket summary -> customer support profile
6. customer ticket summary -> customer summary cache
7. customer ticket summary -> customer support export
8. customer support profile -> training snapshot v1
9. training snapshot v1 -> customer support classifier

## Supported catalog writes and immediate rereads

`seed-datahub` uses the supported DataHub Python SDK and performs exactly 52 proposals/status
operations:

- one `DomainProperties` upsert for `urn:li:domain:forget-me-graph`;
- one `TagProperties` upsert for `urn:li:tag:project-forget-me-graph`;
- for each of the ten allowlisted datasets: `DatasetProperties`, `Domains`, `GlobalTags`, exact
  `UpstreamLineage`, and `set_soft_delete_status(delete=False)`.

Existing evidence custom properties and unrelated tags are preserved. The allocated domain and
fixture lineage are intentionally exact. After emission, the command rereads domain, tag,
properties, domain assignment, tag assignment, lineage, and status for exact equality.

`reset-datahub` calls `set_soft_delete_status(delete=True)` for exactly the ten datasets and rereads
all ten status aspects. It does not delete metadata, domain, tag, or lineage. `restore-datahub` calls
`set_soft_delete_status(delete=False)` for exactly the same ten and rereads status plus the complete
metadata and lineage fixture. Hard deletion is not implemented.

## Exact live context and evidence writeback

After catalog seeding, the workflow initializes the streamable-HTTP MCP client, requires
`get_entities` and `get_lineage`, reads every decision target, and walks downstream from these exact
entrypoints with `upstream=false`, `max_hops=3`, and `max_results=100`:

- `urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)`
- `urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.tickets,PROD)`

Every planned target must be returned inside the allocated namespace. Incomplete lineage, missing
capability, a cross-namespace asset, or a tool error blocks execution before destructive adapters.

Only after approval-bound execution and independent verification, `DatasetPatchBuilder` patches the
allowlisted customers dataset with these `datasetProperties.customProperties` keys:

- `forgetme.request_sha256`
- `forgetme.action` = `verified_deletion_orchestration`
- `forgetme.status`
- `forgetme.plan_sha256`
- `forgetme.certificate_sha256`

The workflow immediately rereads `DatasetPropertiesClass` and requires exact value equality. A
mismatch fails closed and cannot produce a successful write receipt. The raw selector, selector
ciphertext, credentials, and raw MCP responses are never persisted in DataHub evidence.

## Receipts and evidence

Catalog lifecycle receipts are written under:

`APP_STATE_DIR/datahub-catalog/`

- `seed-datahub-receipt.json`
- `reset-datahub-receipt.json`
- `restore-datahub-receipt.json`

They contain operation, timestamp, fixture SHA-256, exact dataset URNs, edge count, domain/tag URNs,
expected and immediately observed soft-delete status, verified aspects, operation count, verified
boolean, and receipt SHA-256. They contain no token, authorization header, selector, or raw response.

For request `<opaque-request-id>`, workflow evidence is under:

`DEMO_FIXTURE_ROOT/evidence/<opaque-request-id>/`

- `certificate.json` and `certificate.md`
- `datahub-read-receipt.json`
- `datahub-write-receipt.json`

The read receipt is persisted before execution/writeback, so an honest write failure retains proof
of the DataHub reads. The request identifier is hashed before writeback.

## Readiness behavior

`GET /api/readiness` is non-mutating and returns 503 unless the fixture marker exists,
`DataHubGraph.test_connection()` succeeds, MCP exposes both required tools, and MCP can read the
configured namespaced probe entity and call downstream lineage. It distinguishes unconfigured,
GMS-unreachable, and MCP-unreachable/incapable states without exposing exception text or secrets.

## Isolation proof

Automated tests prove:

- catalog seeding is idempotent and preserves existing evidence properties and unrelated tags;
- foreign namespaces and namespaced nonfixture targets are rejected before catalog emission;
- extra, partial, and empty soft-reset target sets are rejected before status mutation;
- seed, soft reset, and restore immediately reread the expected aspects and produce sanitized
  receipts;
- cross-namespace MCP assets and non-allowlisted evidence-write targets are rejected;
- incomplete live entity context or lineage blocks execution before destructive adapters;
- an unmarked nonempty local reset directory is refused and its sentinel survives;
- selector values do not appear in MCP arguments, logs, certificates, or DataHub receipts;
- immutable approval hashes, destructive adapter allowlists, idempotency, retraining, independent
  verification, and certificate accuracy remain green.

## Deployment needs and current live-proof status

- Promote only the clean commit reported with this handoff; do not cherry-pick an uncommitted tree.
- Install the documented `datahub` extra in the image.
- Keep the existing service-account token in the coordinator's SecureString mechanism; no value is
  needed in Git or this handoff.
- Preserve port `8103`, the fixed fixture/state roots, domain, tag, and `forgetme.` namespace.
- Run `seed-datahub` before the required live workflow and capture the seed receipt.
- Capture the guarded MCP read, approval-gated local mutation, SDK write/immediate reread, soft reset,
  and restore receipts. Then confirm readiness remains 200 after restore.
- Coordinator owns deployment and rollback. This project must not deploy or access EC2.

The prior deployed commit `477604258142f460bc1946b56f9c685d3cd9e61b` proved truthful
readiness but failed closed because the catalog lacked complete supported lineage. It produced no
live deletion and no DataHub write receipt. This candidate fixes that catalog prerequisite; local
live validation remains unavailable because the Session Manager plugin and a plaintext token are
intentionally absent from this workspace. No live success is claimed until the coordinator promotes
the exact commit and captures the receipts above.
