# Demo and Submission Guide: Forget-Me-Graph

## Current state

The judge-facing product is deployed at
<https://forgetme.datahub-hackathon.aaronmathias.com>, the public repository is
<https://github.com/amathias/forget-me-graph>, and the public captioned demo is
<https://youtu.be/yJXGa730xQ0>. A public-safe judge-console screenshot is included in the
repository. Runtime receipts, private responses, and credentials remain excluded.

Authoritative artifacts:

- [Recording runbook](docs/DEMO_RECORDING.md) — 2:35–2:45 shot list, narration, and redaction gate
- [Devpost copy](SUBMISSION.md) — title, story, DataHub usage, technical proof, and testing steps
- [Defensible claims](docs/CLAIMS.md) — evidence-to-claim matrix and prohibited claims
- [Privacy boundary](docs/PRIVACY.md) — implemented selector and logging boundaries
- [Limitations](docs/LIMITATIONS.md) — exact non-claims and demo constraints
- [Public-safe live hashes](examples/live-evidence-summary.json) — coordinator provenance only
- [Coordinator handoff](COORDINATOR_HANDOFF.md) — exact live operations and promotion needs

## Devpost short description

Forget-Me-Graph is a DataHub-powered deletion and clean-retraining orchestrator. It reads live
entity and downstream-lineage context through the DataHub MCP server, propagates a protected
subject selector through explicit mappings, requires approval for a deterministic action-plan
hash, executes real heterogeneous deletion/rebuild/retraining adapters, independently verifies
each result, and writes receipt-backed evidence through the supported DataHub SDK.

## Three-minute gate

The authoritative recording target is **2:35–2:45**, with a **2:55 hard stop**. The final video must:

1. show the readiness gates, protected request, exact impact graph, deterministic plan, approval,
   live execution, verification matrix, certificate, and supported DataHub writeback;
2. keep the selector masked and omit subject rows, secrets, headers, terminals, and private receipts;
3. state `verified_with_limitations` and the aggregate exemption visibly;
4. call the model action clean-snapshot retraining, not mathematical unlearning;
5. be public, English, under three minutes, and viewable while signed out; and
6. contain no copyrighted music or unauthorized third-party marks.

## Judging evidence map

| Criterion | Visible proof |
|---|---|
| Use of DataHub | Exact live entities/lineage gate plus supported write and immediate reread |
| Technical execution | Privacy boundary, mappings, immutable approval, real adapters, independent verification |
| Originality | One orchestration/evidence loop across data, vectors, caches, exports, snapshots, and model |
| Real-world usefulness | Concrete privacy/ML platform workflow with truthful failure and exemption states |
| Submission quality | Judge console, public-safe examples, reproducible README, concise recording, explicit limits |

## Final external checklist

- [ ] Reconfirm the public application, health endpoint, and readiness endpoint immediately before
  submission.
- [ ] Verify health, readiness, protected planning, approved live execution, downloads, and DataHub
  write/reread before recording without exposing the out-of-band selector secret.
- [x] Capture a public-safe judge-console screenshot without private receipts or selectors.
- [x] Record and publish an under-three-minute demo: <https://youtu.be/yJXGa730xQ0> (2:38).
- [x] Verify the public video while signed out.
- [ ] Add the verified public video URL to the Devpost entry.
- [ ] Confirm the public repository, Apache 2.0 detection, About metadata, and public app availability.
- [ ] Recheck the official Devpost rules and deadline immediately before submission.

## Claims gate

Preferred:

> Forget-Me-Graph uses current DataHub lineage to coordinate and independently verify the
> implemented deletion, rebuild, and clean-retraining paths for a marked synthetic estate, then
> records a receipt-backed result through a supported DataHub write.

Never claim universal forgetting, legal compliance, discovery of uncataloged assets, DataHub hard
deletion, or that the public redacted examples are runtime receipts.
