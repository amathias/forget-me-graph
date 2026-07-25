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
