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
| Status | Live backend vertical slice deployed and coordinator-verified |
| Milestone | Phases 0-4 complete; remaining milestone is the Phase 5/6 judge-facing UI, demo, and submission hardening |
| Current deployed candidate | `8a24421f99622140bfa3e75c8db7ec3923f100de` |
| Prior deployed commits | `477604258142f460bc1946b56f9c685d3cd9e61b` and `478b54128649d68c17454d7562290b30e6c2950e` |
| Prior live findings | `4776042` failed closed on incomplete lineage; `478b541` exposed the absent/reset readiness false positive fixed by `8a24421` |
| Documentation-only handoff commit | Reported by `git rev-parse HEAD` after this handoff is committed; product deployment remains `8a24421` |
| Build command | `python -m pip install -e ".[dev,datahub]"` |
| Test command | `python -m ruff check src tests; python -m pytest --cov=forgetmegraph --cov-report=term-missing -q` |
| Test evidence | 29 passing tests, 89% total coverage, Ruff clean |
| Local demo result | `verified_with_limitations` because the subject-unaddressable aggregate is explicitly exempt |
| Live evidence | Coordinator-owned deployed evidence passed; exact hashes are recorded below |

## Coordinator-owned live validation

These results were captured by the portfolio coordinator against deployed product commit
`8a24421f99622140bfa3e75c8db7ec3923f100de`. They were not reproduced from this project workspace.

### Primary guarded workflow

- Exact catalog seed verified ten active datasets and nine lineage edges.
- The approval-gated workflow completed with `status=verified_with_limitations`, matching the
  documented subject-unaddressable aggregate exemption.

| Evidence | SHA-256 |
|---|---|
| Certificate canonical hash | `0dfc8e519e3cb3d30e037aa46b1b030e06a67d061023ec19ff70a93e61d78e1` |
| `certificate.json` file | `9f1c8c5897a3e04da42924beea7942785ed88736a3da0a153746b0d51ba16b55` |
| `certificate.md` file | `fc20ca8b44c9e1fbbe5b66390034fd208b0d5331d91fbecb3a701e62387f49be` |
| DataHub read receipt | `25dcba1cec326b4f6bf09f1ac4cab3c3a6b2fc4cf6fc838c7ff6e16c9051d7a4` |
| DataHub write/reread receipt | `15dabe47bee2136c0f5915bf4a66c2fcd6e474c25aa4844cc72e8b2d39e8d5c5` |

### Reset, restore, readiness, and isolation

- Exact reset verified all ten project datasets soft-deleted; its canonical receipt SHA-256 has
  prefix `103d2599`.
- The same reset preserved all 102 Lifeboat aspect rows byte-for-byte.
- Exact restore verified all ten datasets active plus all nine edges; its canonical receipt SHA-256
  has prefix `60dbf681`.
- Public readiness transitioned exactly `200 restored -> 503 reset -> 200 restored`.

### Concurrency and immutable snapshot evidence

- Request `coordinator-concurrency-live-002` succeeded concurrently with Lifeboat using separate,
  private, pinned MCP workers.

| Concurrency evidence | SHA-256 |
|---|---|
| DataHub read receipt | `5e210e715a49df004997da437110d1c0c9631b2f070cd0be4a740304ddeb239b` |
| DataHub write/reread receipt | `6776e2e181cd49a94ae1026c544693696b7c5af536065d2b7d1f31e78c70fc73` |
| Certificate | `f5633f7f8579d58cae5ea4a91204027ba6b13dcbcd3f529c4617db655b342268` |

Post-evidence snapshot `snap-06d2125eaa1106558` was mounted read-only, and its certificate hash
matched `f5633f7f8579d58cae5ea4a91204027ba6b13dcbcd3f529c4617db655b342268` exactly.

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

Expected readiness transitions for any rerun (already captured in the coordinator evidence above):

| Catalog state | Expected `/api/readiness` |
|---|---|
| Before `seed-datahub` | HTTP 503; `datahub_catalog=missing_or_invalid` |
| Immediately after verified seed | HTTP 200; `datahub_catalog=ready` |
| Immediately after verified soft reset | HTTP 503; `datahub_catalog=missing_or_invalid` |
| Immediately after verified restore | HTTP 200; `datahub_catalog=ready` |

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

`GET /api/readiness` is non-mutating and returns 503 unless the local fixture marker exists and all
of these current-state checks pass:

1. `DataHubGraph.test_connection()` succeeds.
2. GMS rereads the exact allocated domain and tag, including the project marker.
3. GMS rereads all ten allowlisted datasets as active (`Status.removed=false`).
4. Every dataset has its exact fixture name and required marker properties, allocated domain, and
   required project tag.
5. Every dataset's `UpstreamLineage` exactly matches the nine-edge fixture.
6. MCP exposes `get_entities` and `get_lineage`, returns all ten exact URNs, and returns complete
   downstream coverage from both raw entrypoints.

The endpoint reports `datahub_catalog=missing_or_invalid` before seed, after soft reset, or on any
metadata/lineage drift. It does not trust a prior receipt and performs no writes. It distinguishes
unconfigured, GMS-unreachable, catalog-invalid, and MCP-unreachable/incapable states without
exposing exception text or secrets.

## Isolation proof

Automated tests prove:

- catalog seeding is idempotent and preserves existing evidence properties and unrelated tags;
- foreign namespaces and namespaced nonfixture targets are rejected before catalog emission;
- extra, partial, and empty soft-reset target sets are rejected before status mutation;
- seed, soft reset, and restore immediately reread the expected aspects and produce sanitized
  receipts;
- readiness is 503 before seed and after a verified ten-dataset reset, and returns to 200 only after
  exact seed/restore state plus full MCP coverage;
- readiness rejects dataset-name/marker or exact-lineage drift and emits no metadata/status writes;
- cross-namespace MCP assets and non-allowlisted evidence-write targets are rejected;
- incomplete live entity context or lineage blocks execution before destructive adapters;
- an unmarked nonempty local reset directory is refused and its sentinel survives;
- selector values do not appear in MCP arguments, logs, certificates, or DataHub receipts;
- immutable approval hashes, destructive adapter allowlists, idempotency, retraining, independent
  verification, and certificate accuracy remain green.

## Current deployment and remaining milestone

- The current deployed product candidate is
  `8a24421f99622140bfa3e75c8db7ec3923f100de`.
- The live seed, approved workflow, DataHub write/immediate reread, reset, restore, readiness
  transitions, Lifeboat isolation, concurrent private-MCP run, and read-only snapshot verification
  have passed with the coordinator-owned hashes above.
- This documentation-only successor commit does not require a product deployment; it records the
  evidence while leaving `8a24421` as the deployed application candidate.
- The coordinator continues to own AWS, secrets, deployment, rollback, and evidence retention. No
  credential value was requested or recorded here.
- No further backend fix is requested by the coordinator.

Phases 0-4 of `BUILD_PLAN.md` now have deployed evidence. The remaining project milestone is the
Phase 5/6 judge-facing and submission package:

1. Present the request, live DataHub impact graph and selector mappings, honest action plan,
   approval, execution, verification matrix, certificate, and writeback in a judge-facing UI.
2. Package redacted examples, screenshots, and the coordinator-owned evidence hashes without
   exposing selectors or secrets.
3. Record the public demo under the 2:45 target and complete the repository/Devpost availability,
   Apache 2.0 license, claims, privacy, and final rules audit.
