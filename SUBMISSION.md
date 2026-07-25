# Devpost Submission Package

## Title

Forget-Me-Graph

## Tagline

Trace one deletion through the DataHub graph. Execute every consequence. Prove the result.

## Challenge

**Primary:** Production ML Agents

**Secondary fit:** Agents That Do Real Work

## Short description

Forget-Me-Graph is a DataHub-powered deletion and clean-retraining orchestrator. It reads live
entity and downstream-lineage context through the DataHub MCP server, propagates a protected
subject selector through explicit mappings, requires approval for a deterministic action-plan
hash, executes real purge/rebuild/vector/cache/export/retraining adapters, independently verifies
every result, and writes receipt-backed evidence through the supported DataHub Python SDK.

## Inspiration

A privacy deletion in a system of record says nothing about its downstream copies: transformed
tables, features, embeddings, caches, exports, training snapshots, and models. Data lineage can show
the blast radius, but dataset-level edges cannot tell an executor how to find one subject. Deletion
tools, meanwhile, rarely understand learned artifacts. We built the orchestration and evidence
layer between those worlds.

## What it does

For a marked synthetic customer-support estate, Forget-Me-Graph:

1. accepts a scoped selector and immediately replaces its visible identity with a protected token;
2. requires current DataHub coverage for ten exact assets and nine exact lineage edges;
3. uses versioned key mappings to translate dataset lineage into executable selectors;
4. deterministically selects purge, rebuild, vector deletion/re-index, cache eviction, export
   replacement, clean-snapshot retraining, verification, or exemption;
5. binds human approval to the exact plan SHA-256;
6. mutates real disposable DuckDB, SQLite, CSV, vector, cache, snapshot, and scikit-learn artifacts;
7. independently re-queries every addressable descendant;
8. emits a tamper-evident JSON/Markdown certificate; and
9. writes five allowlisted evidence properties to one allowlisted DataHub dataset, then immediately
   rereads them for exact equality.

The honest result is `verified_with_limitations`: one aggregate has no subject-addressable key and
is explicitly exempt. The model is fully retrained from a rebuilt clean snapshot. We do not claim
mathematical or universal machine unlearning.

## How we use DataHub

- Open-source DataHub is the live catalog and dependency graph.
- The DataHub MCP server supplies `get_entities` and downstream `get_lineage` context.
- Every planned target must be an exact entity returned inside the allocated `forgetme.` namespace.
- GMS rereads verify domain, tag, active state, exact fixture properties, assignments, and exact
  upstream lineage.
- Readiness is non-mutating and fails closed before seed, after soft reset, or on catalog drift.
- The supported Python SDK records request/status/plan/certificate hashes in allowlisted custom
  properties and immediately rereads the aspect.
- DataHub lineage is never mutated by the workflow, and no DataHub entity is hard-deleted.

## How we built it

- Python 3.12, FastAPI, Pydantic
- Open-source DataHub, DataHub MCP server, DataHub Python SDK
- DuckDB and SQLite
- scikit-learn
- Framework-free same-origin HTML/CSS/JavaScript evidence console
- pytest, coverage, Ruff

Keeping the UI same-origin removes a separate credential boundary and lets the console call the
exact planner/executor/verifier used by the CLI. Deterministic code—not an LLM—controls traversal,
policy, approval binding, execution ordering, and status aggregation.

## Technical proof

Coordinator-owned live validation of deployed backend commit
`8a24421f99622140bfa3e75c8db7ec3923f100de` proved:

- 10 active datasets and 9 exact lineage edges;
- a guarded `verified_with_limitations` workflow;
- MCP read and SDK write/immediate-reread receipts;
- readiness `200 restored -> 503 reset -> 200 restored`;
- 102 foreign Lifeboat aspect rows preserved byte-for-byte during reset;
- a successful simultaneous isolated run using separate private MCP workers; and
- an exact certificate match from a read-only post-evidence snapshot.

The public-safe SHA-256 values are committed in `examples/live-evidence-summary.json`. Runtime
receipts and private responses are not committed.

## What is original

Forget-Me-Graph is not another privacy request dashboard and does not stop at lineage
visualization. It combines DataHub's graph with explicit row-key propagation, deterministic action
selection, real heterogeneous adapters, approval binding, independent verification, and evidence
writeback across conventional and learned artifacts.

## What we learned

Successful metadata calls are not proof that an entity exists. DataHub can return an empty response
for an absent or soft-deleted target, so readiness must verify the exact current allocation and
lineage—not infer readiness from configuration or an old receipt. We also learned that honest
machine-unlearning UX needs more than a green check: clean retraining, formal unlearning, exemption,
failure, and out-of-scope are materially different outcomes.

## Testing instructions

```powershell
python -m pip install -e ".[dev,datahub]"
python -m forgetmegraph.demo.seed seed
python -m forgetmegraph.api
```

Open `http://127.0.0.1:8103`. For a credential-free local run, clear **Require live DataHub
read/write** before approval. For the live path, follow the token-safe tunnel and catalog commands
in `COORDINATOR_HANDOFF.md`.

## Public links — complete before submission

- Application: `<PUBLIC_HTTPS_URL>`
- Repository: `https://github.com/amathias/forget-me-graph`
- Demo video: `<PUBLIC_VIDEO_URL>`

These placeholders are intentionally not fabricated. Verify the application and video in a
signed-out browser and recheck the official rules before submitting.

## Submission disclosures

- Built during the hackathon submission period.
- No meaningful pre-existing product code was incorporated.
- Synthetic data is generated by the repository.
- Apache 2.0 licensed.
- No real personal information, secrets, runtime receipts, or copyrighted music/assets are included.
- Limitations and privacy boundaries are documented in `docs/`.
