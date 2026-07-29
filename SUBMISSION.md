# Devpost Submission Package

## Title

Forget-Me-Graph

## Tagline

Trace one deletion through the DataHub graph. Execute every consequence. Prove the result.

## Challenge

**Primary:** Production ML Agents

**Secondary fit:** Agents That Do Real Work

The primary fit is the end-to-end ML response path: DataHub traces raw inputs through features and
a training snapshot to a model, then Forget-Me-Graph rebuilds that path, retrains the toy model,
switches its active manifest, and verifies the replacement. The secondary fit is equally concrete:
the application reads current DataHub context, performs approval-gated work across heterogeneous
stores, and writes the verified result back to DataHub.

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

## Use case and users

The demo represents a privacy operator working with data-platform and ML-platform teams. A single
synthetic subject request must be handled across operational data, derived tables, feature data,
embeddings, caches, exports, a training snapshot, and a learned artifact. The output is not a vague
“done” message: it is an exact plan, an approval record, independently checked results, explicit
limitations, and a downloadable evidence certificate.

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

## Architecture

```text
Same-origin evidence console
  -> privacy boundary and protected selector
  -> live DataHub MCP/GMS context gate
  -> explicit selector mappings + deterministic policy
  -> approval bound to the exact plan SHA-256
  -> allowlisted purge/rebuild/retrain adapters
  -> independent verifier + JSON/Markdown certificate
  -> supported DataHub SDK write + immediate reread
```

No LLM participates in the executable path. Dataset lineage determines impact scope; versioned
selector mappings determine how a subject can be addressed at each descendant. Missing context,
mapping, namespace markers, approval, or verification evidence blocks the relevant work.

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

## Product-relevant challenges

- **A successful metadata call can still mean “not found.”** We replaced configuration inference
  with exact, non-mutating readiness checks for the allocated domain, tag, ten active datasets,
  nine edges, MCP capabilities, and selector-protection contract.
- **Dataset lineage is not row-level lineage.** We introduced explicit, versioned selector mappings
  and fail closed instead of guessing how a subject key propagates.
- **Model replacement is easy to overclaim.** The product verifies a rebuilt subject-free snapshot,
  retired manifest, and fully retrained toy model while explicitly declining to call that universal
  or mathematical unlearning.
- **A shared catalog needs isolation guarantees.** Namespace guards, exact target allowlists,
  reversible soft reset/restore, and immediate rereads prevent this workflow from acting on another
  project.

## Accomplishments

- One approval-gated workflow spans real DuckDB, SQLite, vector, cache, CSV, snapshot, and
  scikit-learn adapters.
- Current DataHub context gates execution, and a supported SDK patch is immediately reread for exact
  evidence equality.
- The certificate distinguishes verified work from the one documented, subject-unaddressable
  aggregate exemption.
- Coordinator validation proved reset/readiness transitions, foreign-project preservation,
  concurrent isolation, and an exact certificate match from a read-only snapshot.
- The public package has 51 passing tests at 90% coverage, deterministic redacted examples, an
  Apache 2.0 license, and clean wheel/source-archive verification.

## Technical proof

Coordinator-owned live workflow validation of backend commit
`8a24421f99622140bfa3e75c8db7ec3923f100de` proved:

- 10 active datasets and 9 exact lineage edges;
- a guarded `verified_with_limitations` workflow;
- MCP read and SDK write/immediate-reread receipts;
- readiness `200 restored -> 503 reset -> 200 restored`;
- 102 foreign Lifeboat aspect rows preserved byte-for-byte during reset;
- a successful simultaneous isolated run using separate private MCP workers; and
- an exact certificate match from a read-only post-evidence snapshot.

The public-safe SHA-256 values are committed in `examples/live-evidence-summary.json`. Runtime
receipts and private responses are not committed. The exact public product now deployed is
`c999d33e2b51485fa4abc84b46ce64d4e91e6b2a`; it preserves that backend and adds the judge console,
truthful selector-secret readiness validation, and pinned DataHub/MCP clients. This documentation
audit did not rerun the live workflow and claims no new receipt or screenshot.

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

Try the public synthetic-data application at
<https://forgetme.datahub-hackathon.aaronmathias.com>. Use synthetic selector `42`, keep it masked,
and review the readiness, plan hash, aggregate limitation, and approval controls before executing.
No account or access token is required. To keep this unauthenticated demo available for every
judge, the service accepts only that one synthetic subject, rejects concurrent execution, and may
return `429` with a short `Retry-After` delay when its transparent plan/run limits are reached.

For a clean local evaluation:

```powershell
python -m pip install -e ".[dev,datahub]"
python -m forgetmegraph.demo.seed seed
python -m forgetmegraph.api
```

Open `http://127.0.0.1:8103`. For a credential-free local run, clear **Require live DataHub
read/write** before approval. For the live path, follow the token-safe tunnel and catalog commands
in `COORDINATOR_HANDOFF.md`.

For adoption beyond the disposable demo, teams provide their own marked fixture or adapter roots,
register exact DataHub namespaces and selector mappings, and implement artifact-specific
verification. Production secrets and DataHub credentials remain out of band; the repository does
not include them. This project is a synthetic reference workflow, not a production compliance
certification.

## Public links

- Application: <https://forgetme.datahub-hackathon.aaronmathias.com>
- Repository: <https://github.com/amathias/forget-me-graph>
- Demo video: Not yet recorded or published. No video or screenshot is claimed by this repository.

Before the final Devpost submission, publish the under-three-minute recording and verify both the
application and video in a signed-out browser.

## Submission disclosures

- Built during the hackathon submission period.
- No meaningful pre-existing product code was incorporated.
- Synthetic data is generated by the repository.
- Apache 2.0 licensed.
- No real personal information, secrets, runtime receipts, or copyrighted music/assets are included.
- No recording or screenshot is claimed until the public video is captured, reviewed, and published.
- Limitations and privacy boundaries are documented in `docs/`.
