# Coordinator Handoff: Forget-Me-Graph

## Relationship to the portfolio coordinator

This project chat owns Forget-Me-Graph's product, code, tests, demo, evidence, and submission. The
portfolio coordinator at `../COORDINATOR_PLAN.md` owns the shared DataHub and AWS deployment
contracts.

Before changing a port, public route, shared environment variable, DataHub namespace, deployment
topology, or global reset behavior, submit the proposed change to the coordinator. Do not edit the
live EC2 host from this project chat.

## Fixed project allocation

| Setting | Value |
|---|---|
| Project slug | `forget-me-graph` |
| Internal port | `8103` |
| DataHub domain | `Demo / Forget-Me-Graph` |
| Required DataHub tag | `project-forget-me-graph` |
| Entity prefix | `forgetme.` |
| Fixture root | `demo/fixtures/forget-me-graph` |
| State root | `/var/lib/datahub-hackathon/forget-me-graph` |

## Project-chat obligations

- Build only Forget-Me-Graph business behavior.
- Keep deletion, rebuilding, retraining, verification, and reset inside this allocation.
- Fail closed if an action or reset target falls outside the `forgetme.` namespace.
- Never place raw subject data or secret values in this handoff.
- Implement `GET /api/health` and `GET /api/readiness`.
- Keep the project independently runnable without the other four submissions.
- Update the milestone handoff below whenever deployment-facing behavior changes.

## Milestone handoff

| Field | Current value |
|---|---|
| Status | `in progress` |
| Milestone | Approval-gated local deletion, rebuild, retraining, verification, and certificate vertical slice |
| Verified commit/artifact | Pending local baseline commit; coordinator records exact hash before promotion |
| Build command | `python -m pip install -e ".[dev]"` |
| Test command | `python -m pytest` |
| Seed command | `python -m forgetmegraph.demo.seed seed` |
| Reset command | `python -m forgetmegraph.demo.seed reset` |
| Demo command | `python -m forgetmegraph.demo.workflow --approved-by <operator> --seed` |
| Run command | `python -m forgetmegraph.api` |
| Internal port | `8103` via `APP_PORT` |
| Health endpoint | `GET /api/health`; verified locally |
| Readiness endpoint | `GET /api/readiness`; fails closed until fixture and live DataHub checks pass |
| Disposable fixture path | `DEMO_FIXTURE_ROOT`, default `demo/fixtures/forget-me-graph` |
| Persistent state path | `APP_STATE_DIR`, deployment value `/var/lib/datahub-hackathon/forget-me-graph` |
| Long-running workers | None; workflow runs synchronously |
| Namespace isolation | `forgetme.` targets required; cross-project targets and unmarked roots are rejected by tests |
| DataHub read | Adapter seam present; live verification pending |
| DataHub writeback | Not yet verified |
| Blockers | Shared DataHub deployment and live read/write receipts; use coordinator SSM tunnel when available |
| Evidence produced | 12 passing tests; nine execution receipts; before/after counts; retired and active model manifests; JSON and Markdown certificates |
| Local demo result | `verified_with_limitations` because the aggregate-only artifact is explicitly exempt |

Required environment variables are documented without secrets in `.env.example`. The local
vertical slice is independently runnable and does not use another portfolio project's code or
runtime. It is not deployable yet because live DataHub MCP reads and supported writeback remain
unverified.

## Required deployment handoff format

When requesting deployment, replace all placeholder or unverified values and include:

1. Exact commit or immutable artifact identifier.
2. Required environment variables without secret values.
3. Build, test, seed, reset, run, and rollback commands.
4. Health/readiness results.
5. DataHub entities, reads, writes, and receipts.
6. Filesystem volumes and disposable paths.
7. Expected CPU, memory, startup time, and job duration.
8. Known limitations and demo concurrency behavior.


