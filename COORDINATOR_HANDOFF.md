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
| Status | Exact release-hardening product deployed; final recording/video/Devpost operations pending |
| Milestone | Judge-facing submission copy and recording checklist finalized without claiming unrecorded media |
| Current deployed product | `c999d33e2b51485fa4abc84b46ce64d4e91e6b2a` at `https://forgetme.datahub-hackathon.aaronmathias.com` |
| Prior deployed commits | `477604258142f460bc1946b56f9c685d3cd9e61b` and `478b54128649d68c17454d7562290b30e6c2950e` |
| Prior live findings | `4776042` failed closed on incomplete lineage; `478b541` exposed the absent/reset readiness false positive fixed by `8a24421` |
| Judge UI code commit | `b9a33f3ac339cfdf26a448ec7c50d143da6721dd`; included in deployed product `c999d33` |
| Prior public candidate | `85828900cc0433bff9f3e0dc5032dcd3a0116c5c` (independently release-reviewed by the coordinator) |
| Deployed release-hardening candidate | `c999d33e2b51485fa4abc84b46ce64d4e91e6b2a` |
| Submission documentation HEAD | This documentation-only successor as reported by `git rev-parse HEAD`; no product-code or new live-evidence claim |
| Build command | `python -m pip install -e ".[dev,datahub]"` |
| Test command | `python -m ruff check src tests; python -m pytest --cov=forgetmegraph --cov-report=term-missing -q` |
| Test evidence | 45 passing tests, 89% total coverage, Ruff clean, JavaScript syntax clean; clean wheel and source-archive installs contain all UI assets and exact DataHub clients |
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

## Judge-facing console milestone

The same FastAPI process now serves a seven-stage evidence console at `/`. It calls the real
planner, executor, verifier, readiness probe, and DataHub integration; there is no simulated client
workflow. New endpoints are:

- `GET /api/demo/overview` — exact executable graph, mappings, defensible claims, and public-safe
  coordinator evidence hashes;
- `POST /api/demo/plan` — protected selector metadata, deterministic decisions, and plan SHA-256;
- `POST /api/demo/run` — explicit approval plus exact plan-hash execution;
- `GET /api/demo/evidence/{request_id}/{file_name}` — exact allowlisted certificate/receipt
  downloads.

Safety properties added for the UI path:

- selector request fields are `repr=False`, validation errors are generic, and responses omit the
  raw value;
- the browser clears the selector field after planning, stores it only in page memory until the
  approved run, and uses no web storage, analytics, or console logging;
- a stale plan hash is rejected before fixture reset or mutation;
- local/test mode can demonstrate real disposable adapters without DataHub, but non-local mode
  forces the live DataHub gate even when the client asks to disable it;
- non-local planning/readiness fail closed unless `FMG_SELECTOR_SECRET` is supplied out of band
  and satisfies the actual selector-protection contract;
- execution is process-serialized for the demo, and evidence downloads accept only four exact
  filenames plus validated opaque request IDs.

### Promotion requirement introduced by this milestone

Supply a minimum-16-character `FMG_SELECTOR_SECRET` through the coordinator's secret mechanism to
every non-local app container. Do not echo it or place it in Git, container arguments, screenshots,
or handoffs. With `APP_ENV` outside `local`/`test`, `/api/readiness` reports
`selector_protection=missing_or_invalid` and returns 503 until the value satisfies the same
contract enforced by planning. Readiness does not derive, hash, persist, log, or return the value.
An absent local/test value uses the bundled disposable fallback; an explicitly invalid value never
does. No port, catalog namespace, DataHub operation, or deployment topology changed.

Clean wheel and source-archive installations verified that `index.html`, `app.css`, and `app.js`
are installed and that the `datahub` extra resolves exactly `acryl-datahub==1.6.0.15` and
`mcp==1.28.1`. The UI regression suite proves redacted planning/validation, approval refusal,
stale-plan refusal before reset, local end-to-end execution and downloads, unallowlisted download
refusal, no browser storage or logging calls, exact coordinator-hash presentation, and the
non-local DataHub/secret gates.

### Release-hardening successor

Readiness now calls the same side-effect-free selector-secret validator used before key derivation.
The controlled-probe regressions cover an absent non-local secret, a 15-character invalid value, a
minimum-valid 16-character value, and the absent local/test fallback. They also prove that response
content does not expose the provided value. The `datahub` optional dependency pins the two exact
coordinator-verified client versions so an archive deployment cannot silently select a different
integration stack.

The coordinator reports exact commit `c999d33e2b51485fa4abc84b46ce64d4e91e6b2a` is now deployed at
the public application URL. This project workspace did not access that deployment. The workflow,
receipt, reset/isolation, concurrency, and snapshot evidence above remains explicitly attributed to
backend commit `8a24421f99622140bfa3e75c8db7ec3923f100de`; no new workflow receipt, screenshot, or recording is
claimed for `c999d33` or this documentation-only successor.

## Public submission package

The repository now includes:

- a judge-oriented README with exact local/live commands, safety boundaries, DataHub proof, and
  repository map plus the actual public application and repository URLs;
- `SUBMISSION.md` with Devpost-ready problem, solution, DataHub usage, technical proof,
  category fit, architecture, use case, adoption summary, challenges, accomplishments, testing
  instructions, disclosures, actual app/repository URLs, and an explicit not-yet-published video
  status;
- `docs/DEMO_RECORDING.md` with a 2:35–2:45 shot list, exact operator sequence and narration,
  preflight, and unchecked frame-level redaction review;
- `docs/CLAIMS.md`, `docs/PRIVACY.md`, and `docs/LIMITATIONS.md` with evidence-bound claims and exact
  non-claims;
- clearly labeled redacted non-runtime request, plan, and certificate examples plus the
  coordinator-owned public hash summary; and
- `docs/assets/forget-me-graph-social-card.png`, a text-only-prompt original 1732×908 image with
  SHA-256 `f131b8dc5404f1153848febf8b6a8119ed284c33fd0081aaa510e784974b9549` and provenance in
  `docs/ASSET_PROVENANCE.md`.

Public-package validation parsed every JSON example, checked local Markdown links, found no external
UI scripts/fonts/images/analytics, found no private key/access-key/bearer-token patterns, and found
no raw selector default in the committed HTML or public examples. Runtime receipts and private live
evidence remain uncommitted.

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

1. Selector protection is present and valid, or the process is explicitly local/test with the
   bundled disposable fallback.
2. `DataHubGraph.test_connection()` succeeds.
3. GMS rereads the exact allocated domain and tag, including the project marker.
4. GMS rereads all ten allowlisted datasets as active (`Status.removed=false`).
5. Every dataset has its exact fixture name and required marker properties, allocated domain, and
   required project tag.
6. Every dataset's `UpstreamLineage` exactly matches the nine-edge fixture.
7. MCP exposes `get_entities` and `get_lineage`, returns all ten exact URNs, and returns complete
   downstream coverage from both raw entrypoints.

The endpoint reports `datahub_catalog=missing_or_invalid` before seed, after soft reset, or on any
metadata/lineage drift and `selector_protection=missing_or_invalid` for an absent or invalid
non-local selector secret. It does not trust a prior receipt and performs no writes. It
distinguishes selector-invalid, unconfigured, GMS-unreachable, catalog-invalid, and
MCP-unreachable/incapable states without exposing exception text or secrets.

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
- readiness rejects absent and short non-local selector secrets, accepts the minimum-valid length,
  and preserves the absent local/test fallback with its DataHub probe independently controlled;
- cross-namespace MCP assets and non-allowlisted evidence-write targets are rejected;
- incomplete live entity context or lineage blocks execution before destructive adapters;
- an unmarked nonempty local reset directory is refused and its sentinel survives;
- selector values do not appear in MCP arguments, logs, certificates, or DataHub receipts;
- immutable approval hashes, destructive adapter allowlists, idempotency, retraining, independent
  verification, and certificate accuracy remain green.

## Current deployment and coordinator actions

- The coordinator reports exact product commit
  `c999d33e2b51485fa4abc84b46ce64d4e91e6b2a` deployed at
  `https://forgetme.datahub-hackathon.aaronmathias.com`.
- Every workflow, readiness-transition, Lifeboat isolation, concurrency, and snapshot result
  recorded above remains attributed to backend commit
  `8a24421f99622140bfa3e75c8db7ec3923f100de`. Deployment of `c999d33` is not represented as a new
  workflow receipt or recording.
- The submission documentation successor is project HEAD after the documentation-only commit; it
  changes no product code, tests, dependencies, runtime configuration, generated evidence, or image
  asset.
- This project did not access AWS, deploy, request a token, copy private receipts, or modify another
  workspace.
- Record the public demo with `docs/DEMO_RECORDING.md`, perform its redaction review, publish the
  under-three-minute video, add the verified video URL to Devpost, verify app/video availability
  while signed out, and recheck the official Devpost rules/deadline. Do not replace the explicit
  pending-video status in Git until a public recording actually exists.
- The coordinator continues to own AWS, secrets, deployment, rollback, public availability,
  screenshots, live recording evidence, and final submission. No further product-code change is
  requested from this workspace.
