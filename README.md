# Forget-Me-Graph

## Submission title

**Forget-Me-Graph: Verified Machine Unlearning and Deletion with DataHub**

## Tagline

Turn a deletion request into verified removal across the entire AI lineage graph.

## One-sentence pitch

Forget-Me-Graph uses DataHub's end-to-end ML lineage to locate every downstream copy and learned artifact affected by a deletion request, selects purge, rebuild, retrain, or unlearning actions, executes them, verifies the result, and issues an evidence certificate.

## Basic idea

Deleting a record from a source database does not remove it from transformed tables, features, training snapshots, vector indexes, caches, exports, or models. Existing tools tend to solve only one piece: privacy request intake, data deletion, lineage visibility, or machine unlearning.

Forget-Me-Graph is the orchestration and evidence layer. DataHub supplies the affected graph and governance context. The agent turns that context into an executable plan, uses adapters appropriate to each artifact type, verifies absence or replacement, and records a complete certificate.

## Why it can win

- **Meaningful DataHub usage:** The end-to-end ML graph determines what must be removed and in what order.
- **A concrete, emotional demo:** Delete one person's data and visibly chase it through the AI stack.
- **Honest technical scope:** The MVP implements purge and retraining for real toy artifacts and treats specialized unlearning algorithms as pluggable adapters.
- **Auditable result:** Every action and verification is linked back to the affected DataHub entities.
- **Distinct from privacy dashboards:** The product executes and proves the request.

## Primary user

Privacy engineers, ML platform teams, data protection officers, data engineers, and AI governance teams.

## Challenge category

Primary: **Production ML Agents**  
Secondary: **Agents That Do Real Work**

## The memorable demo moment

A request for `customer_id=42` enters the system. The agent finds derived rows, a feature snapshot, a vector record, and a toy model; purges or rebuilds each one; reruns verification; and produces a downloadable certificate backed by DataHub lineage.

## Name rationale

“Forget-Me-Graph” is a compact, memorable description of deletion across a dependency graph. The subtitle prevents judges from mistaking it for a generic privacy-request tracker.

## Workspace map

- [Project brief](./PROJECT_BRIEF.md)
- [Build plan](./BUILD_PLAN.md)
- [Demo and submission](./DEMO_AND_SUBMISSION.md)
- [Hackathon rules](./HACKATHON_RULES.md)
- [AI builder instructions](./AGENTS.md)

## Current executable slice

The local vertical slice now performs real, approval-gated mutations against disposable
synthetic artifacts:

- DuckDB row purge and derived-table rebuild;
- vector-record deletion and cache eviction;
- CSV export and training-snapshot replacement;
- full scikit-learn toy-model retraining and active-manifest switch;
- independent before/after verification;
- tamper-evident JSON and Markdown evidence certificates;
- fail-closed namespace, fixture-marker, plan-hash, and readiness checks;
- live DataHub MCP entity/lineage gating for every planned target;
- one allowlisted DataHub SDK evidence write with immediate aspect reread and receipts.

Run and test the complete slice locally:

```powershell
python -m pip install -e ".[dev,datahub]"
python -m ruff check src tests
python -m pytest --cov=forgetmegraph --cov-report=term-missing -q
python -m forgetmegraph.demo.workflow --approved-by demo-privacy-operator --seed
python -m forgetmegraph.api
```

For the live path, start the coordinator-owned GMS and MCP SSM tunnels, supply
`DATAHUB_TOKEN` out of band, then run:

```powershell
$env:DATAHUB_GMS_URL = 'http://127.0.0.1:8080'
$env:DATAHUB_MCP_URL = 'http://127.0.0.1:8000/mcp'
python -m forgetmegraph.demo.workflow --approved-by demo-privacy-operator --seed --require-datahub
```

The coordinator-aligned API listens on port `8103` and exposes `GET /api/health` and
`GET /api/readiness`. Readiness performs real non-mutating GMS connection and MCP
capability/entity/lineage probes; it does not infer readiness from configuration alone.

## First command for the builder

Read `AGENTS.md`, `HACKATHON_RULES.md`, and `PROJECT_BRIEF.md` completely before choosing the implementation stack or writing code.
