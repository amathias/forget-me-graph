# Limitations

- The demonstrated scope is one fixed synthetic customer-support estate represented by ten exact
  DataHub dataset URNs and nine exact lineage edges.
- One aggregate lacks a subject-addressable key and is explicitly exempt. Therefore the expected
  result is `verified_with_limitations`, not an unqualified complete claim.
- The model path rebuilds a subject-free snapshot and fully retrains a toy scikit-learn classifier.
  This is not mathematical proof of machine unlearning and says nothing about arbitrary models.
- DataHub cannot identify offline, uncataloged, or incorrectly cataloged assets. Missing entities,
  incomplete lineage, mapping gaps, or metadata drift fail closed.
- Feature-table and model nodes use DataHub dataset URNs because the supported dataset-lineage API
  represents all nine edges consistently. Their executable types remain explicit custom metadata.
- Evidence SHA-256 hashes are tamper-evident demo controls. They are not signatures, a trusted
  timestamp, an append-only ledger, or legal-grade audit evidence.
- Local mode uses the checked-in executable graph and produces no DataHub read/write receipts.
  Live environments force current DataHub MCP context plus a supported write and immediate reread.
- The web console is intentionally credential-free for judging. It restricts non-local execution
  to synthetic subject `42`, rejects overlapping runs, and applies process-local per-client/global
  limits, but it has no durable rate store, user authentication, multi-tenant authorization,
  distributed denial-of-service protection, or cross-restart resume facility.
- Only synthetic data may be used. The project is not legal advice and does not establish privacy
  law compliance.
- Public URL, repository availability, and video publication are submission operations outside the
  application. Their final values must be verified before Devpost submission.
