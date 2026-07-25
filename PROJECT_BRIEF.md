# Project Brief: Forget-Me-Graph

## Product thesis

A deletion request is complete only when every reachable data and learned artifact has been handled and verified. DataHub supplies the dependency map; Forget-Me-Graph supplies orchestration, execution, and evidence.

## Problem

Organizations often delete a subject from a system of record while leaving traces in:

- transformed tables and snapshots;
- feature stores;
- training datasets and checkpoints;
- vector indexes and caches;
- exports;
- trained models.

Dataset-level lineage alone does not explain how to locate one subject downstream, while deletion tools rarely understand the ML graph.

## MVP scenario

Create a synthetic customer-support estate:

1. `raw.customers` and `raw.tickets`, keyed by `customer_id`.
2. `analytics.customer_ticket_summary`.
3. `features.customer_support_profile`.
4. A training snapshot and toy classifier.
5. A vector index of ticket text with metadata keys.
6. A cache and CSV export.
7. One aggregate with a documented exemption or rebuild-only policy.

Ingest the assets and lineage into DataHub. Store explicit key-propagation mappings for the demo graph. Submit a synthetic deletion request for `customer_id=42`.

## Core user journey

1. Privacy operator submits a request using a scoped subject selector.
2. Service tokenizes or hashes the displayed identifier and keeps raw subject data out of the LLM.
3. Agent reads DataHub lineage, schemas, ownership, and ML metadata.
4. Selector engine propagates the subject key through explicit mappings.
5. Policy engine chooses purge, rebuild, retrain, optional unlearn, verify-only, exempt, or escalate.
6. User reviews the plan and approves destructive work.
7. Executors mutate the local tables, index, cache, export, and toy model.
8. Verifier reruns subject queries, manifest checks, and model lineage checks.
9. Certificate generator reports verified, failed, blocked, exempt, and out-of-scope results.
10. Agent records supported status and evidence references in DataHub.

## Functional requirements

### Request intake and privacy

- Accept a request ID, subject type, scoped selector, legal/policy basis supplied by the fixture, deadline, and requester.
- Minimize subject data in logs and never send raw records to the LLM.
- Support deterministic pseudonymization for the demo.
- Record approval and action history.

### Graph and selector propagation

- Traverse DataHub lineage through datasets, features, training artifacts, models, deployments, and other registered descendants.
- Fetch schema and ownership context.
- Maintain explicit mappings such as `raw.customers.customer_id -> analytics.customer_ticket_summary.customer_id`.
- Stop and escalate when a mapping is missing; never pretend row-level lineage exists when it does not.
- Distinguish direct copies, aggregates, embeddings, learned artifacts, caches, and exports.

### Action planning

- Use deterministic rules to choose:
  - row purge;
  - partition or snapshot rebuild;
  - vector deletion/re-index;
  - cache eviction;
  - export replacement;
  - full retraining;
  - optional registered unlearning adapter;
  - exemption with policy evidence;
  - manual escalation.
- Explain why each action applies and its prerequisites.
- Order destructive and rebuild actions safely.

### Execution and verification

- Implement real local adapters for SQL row deletion/rebuild, vector-record deletion/re-index, cache eviction, export regeneration, and toy-model retraining.
- Verification must query every artifact using the propagated selector where possible.
- For learned artifacts, verify that the old training manifest is retired and the active model points to the rebuilt snapshot; do not call that mathematical proof of forgetting.
- Generate JSON and Markdown evidence certificates.
- Write supported request status/evidence references back to DataHub.

## Suggested architecture

```text
Privacy request UI
  -> request/job API
      -> subject tokenization boundary
      -> DataHub context and ML-lineage adapter
      -> selector-propagation engine
      -> deterministic action policy
      -> approval gate
      -> deletion/rebuild/retrain adapters
      -> verification engine
      -> certificate generator
      -> DataHub writeback + evidence store
```

Suggested stack:

- Python 3.12, FastAPI, Pydantic, NetworkX, pytest.
- React, TypeScript, Vite, graph visualization.
- SQLite for request state and audit history.
- DuckDB, a lightweight vector index, in-memory or SQLite cache, and scikit-learn.
- Docker Compose for repeatability.
- Optional LLM for explanations and human-readable summaries only.

## Core data contracts

### Deletion request

- request ID
- subject type and pseudonymous selector
- scope and policy basis
- deadline
- requester and approver
- request state

### Selector mapping

- source URN and field
- destination URN and field or transformation
- mapping type
- verification query template
- evidence and owner

### Artifact decision

- target URN and lineage path
- artifact type
- propagated selector
- required action
- prerequisites
- policy evidence
- confidence and gaps

### Certificate item

- target and action
- before evidence
- execution receipt
- after verification
- final status
- limitation or exemption

## Safety and truthfulness

- Destructive actions require explicit approval.
- Run only against synthetic, disposable demo data.
- Fail closed on missing selector mappings or incomplete lineage.
- Never expose raw subject data to an external model.
- Do not claim universal machine unlearning.
- Distinguish retraining with a clean snapshot from formal unlearning.
- Make the certificate tamper-evident enough for a demo through hashes, without claiming legal-grade immutability.

## Must-have scope

- Synthetic data only.
- DataHub graph containing data and ML lineage.
- Explicit selector mappings.
- Real purge, vector deletion, cache eviction, export rebuild, and toy retraining.
- Approval and resumable execution.
- Verification and evidence certificate.
- Real supported DataHub writeback.
- Automated tests.

## Stretch scope

- Pluggable SISA-style unlearning adapter.
- Multiple subject identifiers with private set matching.
- Request batching and deadline scheduling.
- DataHub Skill for deletion-impact analysis.
- Signed certificate verification page.

## Out of scope for the MVP

- Guaranteed removal from arbitrary black-box foundation models.
- Production privacy-law advice.
- Discovery of offline assets that are absent from DataHub.
- Handling real personal information.

## Acceptance criteria

- [ ] Raw subject records never enter LLM prompts.
- [ ] The expected downstream graph is discovered from DataHub.
- [ ] Selector mappings produce correct target queries.
- [ ] A missing mapping blocks execution for that branch.
- [ ] Approval is enforced.
- [ ] SQL, vector, cache, export, and toy-model paths actually run.
- [ ] Verification detects a deliberately retained record.
- [ ] The active model manifest references clean training data after retraining.
- [ ] Certificate statuses match evidence.
- [ ] A supported DataHub writeback is visible.

## Competitive positioning

Privacy workflow tools, data deletion systems, and machine-unlearning vendors already exist. The defensible claim is:

> Forget-Me-Graph coordinates and proves deletion across the end-to-end DataHub data and ML graph.

The product is the graph-aware orchestration and evidence layer, not a claim to have solved every unlearning algorithm.
