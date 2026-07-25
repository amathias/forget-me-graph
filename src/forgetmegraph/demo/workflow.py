from __future__ import annotations

import argparse
import json
from pathlib import Path

from forgetmegraph.config import Settings
from forgetmegraph.context.provider import FixtureContextProvider
from forgetmegraph.demo.seed import DEMO_SECRET, seed_estate
from forgetmegraph.domain.models import SubjectSelector
from forgetmegraph.execution.engine import execute_plan
from forgetmegraph.execution.models import Approval
from forgetmegraph.planning.mappings import MappingRegistry
from forgetmegraph.planning.planner import build_action_plan
from forgetmegraph.privacy.selector import SelectorProtector
from forgetmegraph.verification.certificate import EvidenceCertificate, verify_and_certify

CUSTOMERS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)"
TICKETS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.tickets,PROD)"


def run_workflow(
    *,
    root: Path,
    project_root: Path,
    approver: str,
    request_id: str = "req-demo-001",
    selector_secret: str = DEMO_SECRET,
    seed: bool = False,
) -> EvidenceCertificate:
    if seed:
        seed_estate(root, selector_secret=selector_secret)
    context = FixtureContextProvider(project_root / "demo/metadata/graph.json")
    mappings = MappingRegistry.from_json(project_root / "demo/selector-mappings.json")
    protector = SelectorProtector(selector_secret)
    selector = protector.protect(
        SubjectSelector(subject_type="customer", field="customer_id", value="42")
    )
    plan = build_action_plan(
        request_id=request_id,
        selector=selector,
        entrypoint_urns=[CUSTOMERS, TICKETS],
        artifacts=context.artifacts(),
        edges=context.downstream_edges(),
        mappings=mappings,
    )
    approval = Approval.grant(plan, approver=approver)
    receipts = execute_plan(
        root=root,
        plan=plan,
        approval=approval,
        selector=selector,
        protector=protector,
        artifacts=context.artifacts(),
        selector_secret=selector_secret,
    )
    return verify_and_certify(
        root=root,
        plan=plan,
        selector=selector,
        protector=protector,
        artifacts=context.artifacts(),
        receipts=receipts,
        selector_secret=selector_secret,
    )


def main() -> None:
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(
        description="Run the approval-gated synthetic deletion and retraining workflow"
    )
    parser.add_argument("--approved-by", required=True)
    parser.add_argument("--request-id", default="req-demo-001")
    parser.add_argument("--root", type=Path, default=settings.demo_fixture_root)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--seed", action="store_true")
    args = parser.parse_args()
    certificate = run_workflow(
        root=args.root,
        project_root=args.project_root,
        approver=args.approved_by,
        request_id=args.request_id,
        seed=args.seed,
    )
    print(
        json.dumps(
            {
                "request_id": certificate.request_id,
                "selector_token": certificate.selector_token,
                "status": certificate.status.value,
                "certificate_hash": certificate.certificate_hash,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
