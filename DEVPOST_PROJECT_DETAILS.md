# Devpost Project Details: Forget-Me-Graph

This file records the exact judge-facing material for Devpost Step 3. Supporting evidence and
long-form technical detail remain in `SUBMISSION.md` and the public repository.

## About the project

## Inspiration

Deleting a subject from a system of record says nothing about downstream copies in transformed
tables, feature data, embeddings, caches, exports, training snapshots, or models. Data lineage can
show the blast radius, but dataset-level edges do not tell an executor how to find one subject.
Deletion tools, meanwhile, rarely understand learned artifacts.

I built Forget-Me-Graph as the orchestration and evidence layer between those worlds: use
DataHub's graph to identify scope, explicit selector mappings to make each consequence executable,
and independent verification to distinguish proved deletion from a promise.

## What it does

For one fixed synthetic customer-support estate, Forget-Me-Graph:

1. accepts a scoped selector and immediately replaces its visible identity with a protected
   token;
2. requires current DataHub coverage for ten exact assets and nine exact lineage edges;
3. translates dataset lineage into executable subject selectors using versioned key mappings;
4. deterministically selects purge, rebuild, vector deletion and re-indexing, cache eviction,
   export replacement, clean-snapshot retraining, verification, or exemption;
5. binds explicit operator confirmation to the exact plan SHA-256;
6. mutates real disposable DuckDB, SQLite, CSV, vector, cache, snapshot, and scikit-learn
   artifacts;
7. independently re-queries every addressable descendant;
8. creates a JSON and Markdown evidence certificate with a reproducible canonical hash; and
9. writes five allowlisted evidence properties to DataHub and immediately rereads them for exact
   equality.

The demonstrated outcome is intentionally `verified_with_limitations`: nine results are verified,
zero fail, and one aggregate remains exempt because it has no subject-addressable key. The model
is fully retrained from a rebuilt clean snapshot. I do not describe that as mathematical or
universal machine unlearning.

## How I use DataHub

Open-source DataHub is the live catalog and dependency graph. The DataHub MCP Server supplies
`get_entities` and downstream `get_lineage` context. Every target must be an exact entity inside
the allocated `forgetme.*` namespace, and readiness verifies the current domain, tag, active
state, fixture properties, assignments, and exact upstream lineage.

The DataHub Python SDK writes request, status, plan, and certificate hashes to allowlisted custom
properties, followed by an immediate reread. The workflow never mutates DataHub lineage and never
hard-deletes a DataHub entity.

## How I built it

The service uses Python, FastAPI, Pydantic, DuckDB, SQLite, scikit-learn, the DataHub SDK, and the
MCP Python SDK. A same-origin HTML, CSS, and JavaScript evidence console calls the exact planner,
executor, and verifier used by the CLI.

Deterministic code—not an LLM—controls traversal, mapping, action selection, plan-confirmation binding,
execution order, and status aggregation. Missing context, mappings, namespace markers, confirmation,
or verification evidence blocks the relevant work.

## Challenges I faced

A successful metadata call can still mean “not found,” so I replaced configuration inference with
exact non-mutating readiness checks for the complete allocation and MCP capabilities.

Dataset lineage is also not row-level lineage. Guessing how a subject key propagates would be a
privacy defect, so I introduced explicit versioned selector mappings and fail closed when a
mapping is absent.

The final challenge was describing model removal honestly. The product proves a rebuilt
subject-free training snapshot, a retired manifest, and a fully retrained toy model, while keeping
formal unlearning, exemption, failure, and out-of-scope as distinct outcomes.

## What I learned

Metadata availability is not evidence of metadata completeness. Readiness has to verify the exact
current graph rather than trust an old receipt. I also learned that honest unlearning UX needs
more than a green check: a clean retrain, formal unlearning result, documented exemption, failure,
and out-of-scope asset have materially different meanings.

## What I am proud of

- One plan-confirmation-gated workflow spans seven real disposable artifact types.
- Current DataHub context gates execution and supported writeback is verified by reread.
- The certificate separates nine verified results from one explicit limitation.
- Public validation proved reset/readiness transitions and preserved foreign project state.
- The hosted experience uses one masked synthetic subject and requires no judge credential.

## Limitations and what's next

This is a synthetic reference workflow, not a production privacy certification. It supports the
demonstrated mappings and adapters and does not prove that an external estate contains no
unrepresented copy. The current operator confirmation is a demo safety interlock, not authenticated
authorization. Production adoption would require authenticated approval, organization-owned
connectors and mappings, legal review, and platform-specific verification. Next I would add more
learned-artifact adapters and a governed workflow for registering selector mappings.

## Built with

DataHub, MCP, Python, FastAPI, Pydantic, DuckDB, SQLite, scikit-learn, JavaScript, HTML, CSS

## Try it out

1. <https://forgetme.datahub-hackathon.aaronmathias.com>
2. <https://github.com/amathias/forget-me-graph>

## Project media

1. `docs/assets/forget-me-graph-social-card.png` — “Forget-Me-Graph — trace, execute, verify.”
2. `docs/assets/judge-console.png` — “Evidence certificate: nine verified results, zero failures,
   and one explicit limitation.”

## Video demo

<https://youtu.be/8X5DlDZyb4A>
