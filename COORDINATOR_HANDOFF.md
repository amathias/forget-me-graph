# Coordinator Handoff: Forget-Me-Graph

## Relationship to the portfolio coordinator

This project chat owns Forget-Me-Graph's product, code, tests, demo, evidence, and submission. The
portfolio coordinator at `../COORDINATOR_PLAN.md` owns shared DataHub and AWS deployment contracts.
Do not edit EC2 or another project workspace from this project chat.

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
| Status | Code complete; external live validation blocked |
| Milestone | Approval-gated deletion vertical slice with mandatory live MCP context and verified SDK writeback |
| Deployed baseline | `864c31f1bc98670edaf8bdfd7ab7b0930b3f0946` (coordinator deployment before this milestone) |
| New clean commit | Reported by `git rev-parse HEAD` in the final coordinator message after this handoff is committed |
| Build command | `python -m pip install -e ".[dev,datahub]"` |
| Test command | `python -m ruff check src tests; python -m pytest --cov=forgetmegraph --cov-report=term-missing -q` |
| Seed command | `python -m forgetmegraph.demo.seed seed` |
| Reset command | `python -m forgetmegraph.demo.seed reset` |
| Local-only demo | `python -m forgetmegraph.demo.workflow --approved-by demo-privacy-operator --seed` |
| Required live demo | `python -m forgetmegraph.demo.workflow --approved-by demo-privacy-operator --seed --require-datahub` |
| Run command | `python -m forgetmegraph.api` |
| Health | `GET /api/health`; non-mutating process health |
| Readiness | `GET /api/readiness`; real GMS connection plus MCP capability/entity probes; no write |
| Test evidence | 21 passing tests, 88% total coverage, Ruff clean |
| Local demo result | `verified_with_limitations` because the subject-unaddressable aggregate is explicitly exempt |
| Live evidence | Not produced in this workspace; see blockers below |

## Exact local tunnel and live-run commands

Run the tunnels in two separate PowerShell terminals from this workspace:

```powershell
powershell -ExecutionPolicy Bypass -File ..\infra\scripts\open_tunnel.ps1 -Service gms
powershell -ExecutionPolicy Bypass -File ..\infra\scripts\open_tunnel.ps1 -Service mcp
```

In the application terminal, set only the non-secret connection settings. The coordinator supplies
`DATAHUB_TOKEN` out of band; do not echo it or save it in a file.

```powershell
$env:DATAHUB_GMS_URL = 'http://127.0.0.1:8080'
$env:DATAHUB_MCP_URL = 'http://127.0.0.1:8000/mcp'
$env:DATAHUB_URN_PREFIX = 'forgetme.'
$env:DATAHUB_PROBE_URN = 'urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)'
python -m pip install -e ".[dev,datahub]"
python -m ruff check src tests
python -m pytest --cov=forgetmegraph --cov-report=term-missing -q
python -m forgetmegraph.demo.workflow --approved-by demo-privacy-operator --seed --require-datahub
python -m forgetmegraph.api
```

Non-mutating endpoint checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8103/api/health
Invoke-RestMethod http://127.0.0.1:8103/api/readiness
```

## Exact DataHub reads

The live workflow uses the official streamable-HTTP MCP client with bearer authentication. It first
lists tools and requires both `get_entities` and `get_lineage`.

1. `get_entities` receives the sorted URNs of every decision target in
   `demo/metadata/graph.json`. Every returned data asset must contain `forgetme.` and every planned
   target must be present.
2. `get_lineage` is called for each exact entrypoint below with
   `upstream=false`, `max_hops=3`, and `max_results=100`:
   - `urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)`
   - `urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.tickets,PROD)`
3. The union of the entrypoints and returned downstream assets must contain every planned target.
   An incomplete graph, missing capability, cross-namespace asset, or tool error blocks execution.

Only URNs and response hashes are persisted. Raw MCP responses, credentials, and selector values are
not written to evidence.

## Exact supported DataHub write and reread

Writeback occurs only after approval-bound local execution and independent certificate generation.
The only target is the explicitly allowlisted entrypoint:

`urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)`

The supported Python SDK `DatasetPatchBuilder` patches these `datasetProperties.customProperties`
keys through `DataHubGraph.emit`:

- `forgetme.request_sha256`
- `forgetme.action` = `verified_deletion_orchestration`
- `forgetme.status`
- `forgetme.plan_sha256`
- `forgetme.certificate_sha256`

The workflow immediately calls `DataHubGraph.get_aspect(..., DatasetPropertiesClass)` and compares
all five observed values with the intended values. Any mismatch fails the live workflow and does not
produce a successful write receipt. No DataHub deletion, lineage mutation, tag mutation, or entity
mutation is performed.

## Receipts and evidence

For request `<opaque-request-id>`, local evidence is under:

`DEMO_FIXTURE_ROOT/evidence/<opaque-request-id>/`

- `certificate.json` and `certificate.md`: independently verified deletion/rebuild/retrain result.
- `datahub-read-receipt.json`: entrypoint URNs, observed entity/lineage URNs, capability names, and
  SHA-256 hashes of the two response groups.
- `datahub-write-receipt.json`: target, operation, intended properties, immediately observed
  properties, verification boolean, and receipt SHA-256.

The request ID itself is hashed before DataHub writeback. Selector ciphertext, raw selector values,
and credentials are absent from both DataHub receipts. The read receipt is saved before writeback so
read evidence remains available if the write fails honestly.

## Readiness behavior

`GET /api/readiness` is non-mutating and returns 503 unless all of these checks pass:

1. The allocated fixture marker exists.
2. `DataHubGraph.test_connection()` succeeds against GMS.
3. MCP initializes and exposes `get_entities` and `get_lineage`.
4. MCP can read the configured namespaced probe entity and call its downstream lineage tool.

The response distinguishes unconfigured, GMS-unreachable, and MCP-unreachable/incapable states
without returning exception text or credentials.

## Isolation proof

Automated tests prove:

- cross-namespace MCP assets and non-allowlisted write targets are rejected;
- incomplete entity context or lineage blocks execution before destructive adapters run;
- MCP arguments and receipts contain no raw demo selector;
- an unmarked nonempty reset directory is refused and its sentinel file survives;
- the existing fixture marker, immutable approval hash, adapter allowlists, idempotency, failed
  verification, retraining, and certificate tests remain green;
- an integrated live-mode test persists both DataHub receipts around the existing real local
  deletion/rebuild/retrain path.

## Deployment needs

- Install the package with the `datahub` extra.
- Supply `DATAHUB_TOKEN` only through the coordinator's secret mechanism.
- Configure the canonical GMS/MCP URLs shown above (or coordinator-approved deployment equivalents).
- Preserve port `8103`, the allocated fixture/state roots, and the `forgetme.` namespace.
- Seed the disposable fixture before expecting readiness to pass.
- Do not deploy this project-chat commit from here; coordinator owns deployment and rollback.

Rollback after coordinator deployment should restore the prior immutable artifact
`864c31f1bc98670edaf8bdfd7ab7b0930b3f0946` using the coordinator's existing deployment process.

## Current blockers and live proof status

Local live validation remains unavailable because AWS CLI reports that the Session Manager Plugin
is not installed; both standard Windows install paths are absent, so
`..\infra\scripts\open_tunnel.ps1` cannot establish either tunnel. A DataHub credential is also
intentionally not exported into this project workspace.

The coordinator confirmed that a dedicated DataHub service-account token is stored as AWS
SecureString and loaded into MCP and all five live app containers. No secret value was requested or
received here, so deployment credential configuration is no longer a blocker.

No claim of live DataHub connectivity, live namespace contents, write success, or live reread is
made by this local handoff. The coordinator owns promotion of the exact commit below and will capture
guarded live read, write, immediate reread, and restore evidence. Readiness must remain 503 until its
real non-mutating probes pass in that environment.
