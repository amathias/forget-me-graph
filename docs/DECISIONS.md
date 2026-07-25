# Architecture Decisions

## ADR-001: Deterministic core with a narrow agent boundary

**Status:** Accepted

DataHub MCP supplies live catalog context. Selector propagation, policy selection,
execution ordering, verification, and certificate aggregation remain deterministic
application code. Any LLM integration receives only URNs, schemas, counts, policy
metadata, gaps, and pseudonymous selector tokens.

## ADR-002: Encrypted selector persistence

**Status:** Accepted

The intake selector is HMAC-tokenized for display and encrypted for resumable
execution. Only artifact adapters may decrypt it. Logs, UI events, plans, and
certificates use the pseudonymous token.

## ADR-003: Risk-first DataHub integration

**Status:** Accepted

Open-source DataHub and its self-hosted MCP server provide live entity and downstream-lineage
context. Deterministic fixture metadata still defines executable adapters and explicit selector-key
mappings, but live MCP must prove every planned target exists in the allocated namespace and is
reachable from the two entrypoints before execution starts. This retains deterministic action
selection while making DataHub context a mandatory fail-closed gate in live mode.

## ADR-004: Clean retraining is not formal unlearning

**Status:** Accepted

The MVP rebuilds a training snapshot, retrains a toy model, retires the old manifest,
and switches the active model pointer. Certificates state exactly that and make no
claim of mathematical forgetting.

## ADR-005: Approval binds to an immutable plan hash

**Status:** Accepted

Approval records the request ID, approver, timestamp, and exact action-plan hash. Execution
rejects stale approval if traversal, mappings, policy, or targets change. Approval alone is not
enough: every destructive target must also pass the fixture-marker and `forgetme.` namespace
checks.

## ADR-006: Evidence is independently derived after execution

**Status:** Accepted

Adapter success messages do not determine certificate status. The verifier re-queries every
subject-addressable store and checks the active training/model manifest. Missing receipts,
retained records, or blocked mappings produce an incomplete certificate. Aggregate exemptions
produce `verified_with_limitations`, never an unqualified complete result.
## ADR-007: Narrow, receipt-backed DataHub writeback

**Status:** Accepted

Forget-Me-Graph writes only evidence custom properties on the allowlisted source dataset through the
supported DataHub Python SDK. It never mutates shared lineage or deletes DataHub entities. The
request identifier is hashed, and the property values contain only action status and evidence
hashes. A successful receipt requires an immediate reread of `datasetProperties` with exact value
matching. Readiness performs only connection, capability, entity, and lineage reads.

## ADR-008: Exact, soft-deletable DataHub catalog fixture

**Status:** Accepted

DataHub's supported dataset-lineage API represents all ten demo nodes as dataset URNs. The feature
table and model retain their executable `feature_table` and `ml_model` semantics in allowlisted
`datasetProperties.customProperties`; this avoids unsupported cross-entity lineage while preserving
the planner and adapter behavior.

The catalog lifecycle command accepts only the fixed `forgetme.` ten-URN fixture and exact nine-edge
graph. Seeding upserts the allocated domain, tag, dataset properties, domain assignments, tags, and
transformed lineage, clears soft-delete status, then immediately rereads every aspect. Reset changes
only those ten datasets to soft-deleted status; restore clears that status and rereads the complete
fixture. Hard deletion is deliberately unsupported. Each operation writes a sanitized receipt with
the fixture hash, exact URNs, observed status, verified aspects, and a receipt hash.

## ADR-009: Readiness requires the complete active catalog allocation

**Status:** Accepted

Connectivity and MCP capability discovery alone cannot establish readiness: DataHub may return an
empty successful response for an absent or soft-deleted probe entity. Readiness therefore performs
non-mutating GMS rereads of the allocated domain/tag and all ten datasets, requiring active status,
exact fixture names and marker properties, required domain/tag assignments, and exact nine-edge
upstream lineage. Only then does it require MCP entity coverage for all ten URNs and complete
downstream coverage from both entrypoints.

No seed receipt is trusted as current state, and readiness never writes. Before seed, after soft
reset, or after metadata/lineage drift it returns 503 with `datahub_catalog=missing_or_invalid`.
Successful seed or restore must make the same live checks pass before readiness returns 200.

## ADR-010: Same-origin judge console reuses the deterministic core

**Status:** Accepted

The judge console is served by the existing FastAPI process and calls narrow plan, execution,
overview, readiness, and evidence-download endpoints. It does not reimplement workflow logic in the
browser. The plan endpoint returns only a protected token and deterministic decisions; execution
requires the same request selector plus the exact approved plan hash, and rejects a stale hash
before fixture reset. Non-local environments force the live DataHub gate even if a client asks to
disable it. Evidence downloads use a fixed filename allowlist.

This keeps browser state ephemeral, avoids a second credential boundary, and makes UI claims match
the CLI workflow. The process-local execution lock is appropriate for the demo but is not presented
as durable job orchestration.

## ADR-011: Public evidence contains provenance hashes, not private receipts

**Status:** Accepted

The repository records coordinator-owned live evidence as exact SHA-256 values and bounded
observations in `examples/live-evidence-summary.json`. It does not copy runtime receipts, raw MCP
responses, selector-derived values, credentials, or private infrastructure evidence into Git.
Plan/request/certificate examples are clearly labeled redacted and non-runtime so they cannot be
mistaken for executed proof. Operational evidence remains under configured runtime state roots.
