# Builder Instructions: Forget-Me-Graph

## Mission

Build a working, judge-ready vertical slice of Forget-Me-Graph: a DataHub-powered deletion and machine-unlearning orchestrator with verifiable evidence.

## Read first

Before modifying code, read these files completely:

1. `HACKATHON_RULES.md`
2. `PROJECT_BRIEF.md`
3. `BUILD_PLAN.md`
4. `DEMO_AND_SUBMISSION.md`

## Non-negotiable product behavior

- Read real data and ML lineage from open-source DataHub through an eligible integration.
- Demonstrate real writeback to DataHub through a supported API or SDK.
- Accept a scoped deletion subject selector and never expose unnecessary subject data in logs or prompts.
- Map dataset-level lineage to executable deletion adapters using explicit key-mapping metadata.
- Execute real purge, rebuild, and toy-model retraining paths; treat specialized unlearning algorithms as optional adapters unless genuinely implemented.
- Verify absence or replacement at every in-scope descendant.
- Produce a certificate that distinguishes verified, failed, blocked, and out-of-scope artifacts.
- Require approval for destructive actions.

## Engineering principles

- Privacy claims must match implemented behavior exactly.
- Never send raw personal data to an LLM; use identifiers, counts, schemas, and policy metadata.
- Keep deterministic traversal, action selection rules, and verification separate from LLM narration.
- Make jobs idempotent and resumable.
- Redact subject identifiers in UI screenshots, logs, and sample artifacts where practical.
- Test selector propagation, key mappings, incomplete lineage, deletion failures, retraining, and certificate accuracy.
- Maintain `docs/DECISIONS.md` as architectural decisions are made.

## GitHub publishing

- Canonical repository: `https://github.com/amathias/forget-me-graph`.
- Configured origin: `git@github-datahub-forget-me-graph:amathias/forget-me-graph.git`.
- While this chat is the project's primary writer, it may commit and intermittently push verified
  milestone changes to `origin/main`.
- Inspect the complete diff, run relevant checks, stage only intended paths, and keep
  `COORDINATOR_HANDOFF.md` current before pushing.
- Never change the remote, force push, delete remote refs, use another project's SSH alias, or add
  secrets, private keys, `.env` files, runtime receipts, or private evidence to Git.
- If `origin` is absent or differs from the exact value above, stop and escalate to the portfolio
  coordinator.

## Definition of done

A reviewer can submit the demo deletion request, inspect affected assets, approve the plan, watch real local tables and vector records be purged and a toy model retrained, rerun verification, see DataHub updates, and download a truthful evidence certificate.

## Submission guardrails

- The repository must be public and contain an Apache 2.0 `LICENSE`.
- The work must be newly built during the submission period.
- Disclose any meaningful pre-existing code or assets.
- Keep the title independent: “Forget-Me-Graph,” described as DataHub-powered.
