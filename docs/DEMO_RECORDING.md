# Demo Recording Runbook

Target runtime: **2:35–2:45**. Hard stop: **2:55**.

Recording status: **not yet recorded or published**. This runbook is a checklist, not evidence that
a video or screenshot already exists.

## Before recording

- [ ] Open <https://forgetme.datahub-hackathon.aaronmathias.com> and confirm the coordinator still
  identifies the deployed product as exact commit
  `c999d33e2b51485fa4abc84b46ce64d4e91e6b2a`.
- [ ] Confirm the exact catalog is restored and `/api/readiness` returns HTTP 200 with fixture and
  selector protection `ready`, DataHub catalog `ready`, GMS/MCP `connected`, and MCP capabilities
  `get_entities` and `get_lineage`.
- [ ] Open the evidence console in a clean browser window at 1440×900 or larger and 100% zoom. Set
  request ID `judge-recording-001`, enter synthetic demo selector `42` before capture, and leave
  the field masked.
- [ ] Keep the selector field masked. Close developer tools, terminals containing environment
   variables, AWS consoles, secret managers, unrelated tabs, and notifications.
- [ ] Prepare DataHub in a second tab at the allowlisted customers dataset, with the visible
   `forgetme.*` evidence properties and lineage graph. Do not expose authorization headers, raw MCP
   responses, selectors, or private receipts.
- [ ] Leave approver `demo-privacy-operator`, **Reset synthetic fixture first**, and **Require live
  DataHub read/write** selected.
- [ ] Record without copyrighted music, unrelated third-party marks, or personal notifications.

## Exact operator sequence

1. Start on the hero with the HTTP 200 execution gates visible.
2. Scroll to Request and submit the already-masked synthetic selector.
3. Pause on the protected token, plan SHA-256, ten-node graph, and versioned mapping explanation.
4. Scroll through the action table and point out the aggregate exemption.
5. Select the approval checkbox and execute with both safety checkboxes still selected. If the
   public service reports a transparent `429` capacity delay, wait for the displayed `Retry-After`
   interval and retry once; do not repeatedly submit.
6. Keep the execution timeline visible until verification and write/reread complete.
7. Show the verification matrix, `verified_with_limitations`, and certificate download buttons.
8. Switch to the prepared DataHub tab and show only the lineage plus allowlisted `forgetme.*`
   properties.
9. Return to the console proof strip, deliver the closing line, and stop by 2:55.

## Shot list and narration

### 0:00–0:18 — Problem and proof target

**Screen:** Hero, execution gates, and proof strip.

> Deleting a source row does not remove its features, embeddings, exports, training snapshot, or
> learned artifact. Forget-Me-Graph uses DataHub to trace one synthetic request through that graph,
> execute the required work, and prove the result.

### 0:18–0:42 — Privacy-scoped request

**Action:** Scroll to Request. Leave the already-entered selector masked and submit the synthetic
request.

> The raw selector crosses only the intake boundary. The visible workflow uses a protected token.
> No subject record or raw selector goes to an LLM—this workflow is deterministic.

### 0:42–1:02 — Exact DataHub impact graph

**Screen:** Ten-node impact graph and mapping caption.

> Live MCP entity and downstream-lineage reads must cover all ten allowlisted assets and nine
> edges. Dataset lineage defines scope; versioned selector mappings explain how the subject can be
> addressed downstream. Any gap fails closed.

### 1:02–1:25 — Honest action plan and approval

**Screen:** Action table, plan hash, aggregate exemption, approval card.

> Rules select row purge, rebuild, vector deletion, cache eviction, export replacement, and clean
> retraining. This aggregate has no subject key, so it is exempt instead of being falsely marked
> deleted. Approval binds to this exact SHA-256 plan.

**Action:** Check the approval box and execute with both **Reset synthetic fixture first** and
**Require live DataHub read/write** still selected.

### 1:25–2:00 — Real execution

**Screen:** Execution timeline.

> The marked disposable estate is reset, then real DuckDB, SQLite, CSV, vector, cache, snapshot,
> and scikit-learn adapters run. The verifier issues fresh queries; it does not trust adapter success
> messages.

### 2:00–2:25 — Verification and certificate

**Screen:** Verification matrix and certificate.

> Every addressable descendant is absent or replaced. The active model now points to a rebuilt
> subject-free snapshot. The result is verified with limitations—not a claim of mathematical
> unlearning—and the certificate is available as JSON or Markdown.

### 2:25–2:40 — DataHub writeback and isolation close

**Screen:** DataHub tab showing allowlisted `forgetme.*` custom properties, then console live proof.

> Only after verification, a supported DataHub SDK patch records status and evidence hashes and
> immediately rereads them. Live reset testing preserved 102 foreign rows, readiness failed while
> this catalog was reset, and an isolated concurrent run produced the same evidence chain.

### 2:40–2:45 — Closing line

> Forget-Me-Graph turns lineage into provable deletion work—without pretending retraining is
> universal forgetting.

## Redaction review

- [ ] Selector input remained masked in every frame.
- [ ] No raw fixture rows, subject name, request body, token value, secret, authorization header, MCP
  payload, terminal history, or private receipt appeared.
- [ ] Certificate limitation and `verified_with_limitations` status are legible.
- [ ] DataHub lineage and supported evidence properties are legible.
- [ ] No narration calls clean-snapshot retraining mathematical or universal unlearning.
- [ ] The video is public, English, under three minutes, and works in a signed-out browser.
- [ ] The public app and repository links are correct in `SUBMISSION.md`; after publication, add the
  verified video URL to the Devpost entry and replace the explicit pending-video status only if the
  repository copy is intentionally refreshed.
