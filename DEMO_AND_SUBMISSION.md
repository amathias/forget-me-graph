# Demo and Submission Guide: Forget-Me-Graph

## Devpost short description

Forget-Me-Graph is a DataHub-powered deletion and machine-unlearning orchestrator. It traces a scoped subject request through data and ML lineage, propagates selectors using explicit mappings, executes approved purge, rebuild, vector deletion, cache eviction, and toy retraining actions, verifies every result, and creates an evidence certificate.

## Three-minute demo target

Aim for **2 minutes 35 seconds to 2 minutes 45 seconds**.

### 0:00–0:20 — Prove the problem

Show synthetic `customer_id=42` present in a source, derived table, vector result, export, and active training manifest.

> Deleting a source row does not remove its derived features, embeddings, exports, caches, or learned artifacts.

### 0:20–0:52 — Request and graph

Submit the synthetic request. Show pseudonymization, live DataHub data/ML lineage, and selector mappings.

> Raw subject records never enter the language model. DataHub identifies affected assets, while explicit key mappings explain how the selector propagates.

### 0:52–1:22 — Plan honestly

Show purge, rebuild, retrain, verify, and one blocked/exempt state. Approve.

> The agent distinguishes deletion, clean retraining, optional unlearning, exemptions, and missing evidence rather than making one vague “forgotten” claim.

### 1:22–2:08 — Execute

Show SQL deletion/rebuild, vector deletion, cache eviction, export regeneration, and toy retraining.

> The demonstrated paths execute against real disposable artifacts and emit receipts.

### 2:08–2:32 — Verify and certify

Repeat the subject queries, show the clean active model manifest, certificate status, and DataHub writeback.

> The certificate is derived from verification evidence. A failed or unmapped branch prevents a false complete result.

### 2:32–2:43 — Close

> Forget-Me-Graph turns end-to-end lineage into provable deletion operations.

## Submission narrative

### Problem

Privacy deletion, data cleanup, vector-store deletion, and model retraining are handled by separate systems. A source deletion therefore does not prove removal across an AI stack.

### Solution

Forget-Me-Graph combines DataHub lineage with explicit selector mappings, deterministic action rules, artifact adapters, and verification to coordinate a complete request.

### What makes it original

It is the graph-aware orchestration and evidence layer across conventional stores and learned artifacts, not a generic privacy-request dashboard or an unsupported universal-unlearning claim.

### DataHub usage to state explicitly

- Reads schemas, ownership, data lineage, and ML lineage.
- Uses the graph to find descendants and order actions.
- Uses an eligible DataHub agent integration in the live flow.
- Writes supported request/evidence context back into DataHub.

## Judging evidence map

| Criterion | What judges should see |
|---|---|
| Use of DataHub | Live data-to-model graph drives scope and visible writeback |
| Technical execution | Privacy boundary, mappings, real adapters, approval, verification, certificate |
| Originality | One orchestrated evidence loop across data, vectors, caches, exports, and model |
| Real-world usefulness | Concrete subject-request workflow for privacy and ML teams |
| Submission quality | Synthetic reproducible demo, precise claims, examples and limitations |

## Required repository evidence

- `examples/deletion-request.json` with synthetic identifiers
- `examples/selector-mappings.json`
- `examples/action-plan.json`
- `examples/evidence-certificate.md`
- before/after queries and training manifests
- DataHub screenshots
- privacy and limitations documentation

## Claims to avoid

- “Guarantees that any model has forgotten a person.”
- “Implements every machine-unlearning technique.”
- “Provides legal compliance.”
- “Finds assets absent from the catalog.”

Prefer: “Coordinates and verifies the implemented deletion, rebuild, and retraining paths for assets represented in the demo DataHub graph.”

## Recording checklist

- [ ] Synthetic data only.
- [ ] Video is public and under three minutes.
- [ ] Raw synthetic records are not shown in prompts or logs.
- [ ] DataHub data and ML lineage are visible.
- [ ] Real purge/rebuild/retrain actions are shown.
- [ ] Certificate limitations are legible.
- [ ] No secrets or copyrighted music appears.
