# Build Plan: Forget-Me-Graph

## Delivery strategy

Build an honest, verifiable deletion path before adding exotic unlearning. The critical proof is:

> One synthetic subject selector propagates through a live DataHub graph, drives real purge/rebuild/retrain actions, and produces evidence that matches what was actually verified.

## Recommended repository shape

```text
/
  app/                  # API, selector propagation, policy, jobs
  web/                  # request, graph, approval, certificate UI
  adapters/             # DataHub and artifact executors
  demo/                 # synthetic data/ML/RAG estate and reset
  examples/             # requests and evidence certificates
  tests/
  docs/
  docker-compose.yml
  .env.example
  LICENSE
  README.md
```

## Phase 0: Establish the privacy boundary and DataHub connection

- Pin and start open-source DataHub.
- Ingest a tiny data-to-model graph.
- Read through MCP or Agent Context Kit and prove one supported writeback.
- Define what data may enter logs, prompts, evidence, and UI.
- Add tests that raw synthetic records never reach the LLM adapter.

Exit condition: connectivity works and privacy boundaries are executable tests.

## Phase 1: Build the synthetic estate

- Generate customers and support tickets with `customer_id`.
- Build derived table, feature snapshot, vector index, cache, export, and toy model.
- Add an explicit artifact manifest and reliable reset.
- Ingest schemas, owners, lineage, and ML relationships into DataHub.

Exit condition: `customer_id=42` is demonstrably present in every intended direct descendant before deletion.

## Phase 2: Selector propagation and graph planning

- Define typed request, selector mapping, artifact decision, action, evidence, and certificate schemas.
- Implement explicit field mappings.
- Traverse live DataHub lineage and attach mappings.
- Stop on a deliberately missing mapping.
- Unit-test direct copies, aggregates, embeddings, model artifacts, unaffected branches, and missing evidence.

Exit condition: the plan correctly classifies every demo artifact without an LLM.

## Phase 3: Execution adapters

- Implement SQL deletion and rebuild.
- Implement vector deletion/re-index.
- Implement cache eviction.
- Implement export regeneration.
- Implement clean-snapshot toy-model retraining and active-manifest switch.
- Add approval, idempotency, retry, and resume.

Exit condition: real local artifacts change and a reset reproduces the starting state.

## Phase 4: Verification and certificate

- Query direct stores using propagated selectors.
- Verify manifests and active versions for rebuilt/learned artifacts.
- Distinguish verified, failed, blocked, exempt, and out-of-scope.
- Inject one incomplete action and prove the certificate refuses “complete.”
- Generate stable JSON and Markdown certificates with evidence hashes.
- Write supported status/evidence references to DataHub.

Exit condition: certificate status is derived from evidence rather than agent prose.

## Phase 5: Judge-facing UI

Required screens:

1. Synthetic deletion request.
2. DataHub impact graph and selector mappings.
3. Action plan with limitations.
4. Approval.
5. Live execution.
6. Verification matrix.
7. Certificate and DataHub writeback.

Always label retraining separately from formal machine unlearning.

## Phase 6: Hardening

- Add examples and screenshots.
- Test setup from clean checkout.
- Add Apache 2.0 license.
- Add privacy, threat, and limitation documentation.
- Pin dependencies and scan for secrets.
- Record a demo under 2:45.

## Test plan

### Unit

- Request redaction.
- Selector mappings.
- Graph traversal and classifications.
- Deterministic action policy.
- Approval and idempotency.
- Certificate status aggregation.

### Integration

- DataHub read/write.
- SQL, vector, cache, export, and model adapters.
- Missing mapping failure.
- Retry and resume.
- Evidence hashes and report generation.

### End to end

- Seed synthetic estate.
- Prove subject presence.
- Submit and approve request.
- Execute actions.
- Prove subject absence or documented limitation.
- Confirm clean model manifest.
- Confirm DataHub update and certificate.

## Scope cuts if behind

Cut in this order:

1. Formal unlearning adapter.
2. Batch requests.
3. Signed certificate UI.
4. Multiple subject-key types.
5. Advanced exemption workflows.

Never cut privacy boundaries, explicit selector mappings, real deletion/retraining, verification, or DataHub writeback.

## Evidence to preserve

- Redacted request.
- DataHub lineage paths.
- Selector mapping manifest.
- Before/after store queries.
- Model training manifests.
- Execution and verification receipts.
- Certificate.
- DataHub before/after screenshots.

## Final engineering checklist

- [ ] Synthetic data only.
- [ ] No raw subject data enters an LLM prompt.
- [ ] Missing mappings fail closed.
- [ ] Destructive work requires approval.
- [ ] “Retrained” is not mislabeled “mathematically unlearned.”
- [ ] Reset and rerun work reliably.
- [ ] CI covers the privacy and evidence contracts.
- [ ] README maps proof to judging criteria.
