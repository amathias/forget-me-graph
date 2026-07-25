from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from forgetmegraph.config import Settings
from forgetmegraph.context.datahub import (
    DataHubIntegrationError,
    DataHubMcpReader,
    StreamableHttpMcpClient,
    create_graph_client,
    write_evidence_properties,
)
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
    require_datahub: bool = False,
    settings: Settings | None = None,
) -> EvidenceCertificate:
    if seed:
        seed_estate(root, selector_secret=selector_secret)
    context = FixtureContextProvider(project_root / "demo/metadata/graph.json")
    artifacts = context.artifacts()
    edges = context.downstream_edges()
    mappings = MappingRegistry.from_json(project_root / "demo/selector-mappings.json")
    protector = SelectorProtector(selector_secret)
    selector = protector.protect(
        SubjectSelector(subject_type="customer", field="customer_id", value="42")
    )
    plan = build_action_plan(
        request_id=request_id,
        selector=selector,
        entrypoint_urns=[CUSTOMERS, TICKETS],
        artifacts=artifacts,
        edges=edges,
        mappings=mappings,
    )
    read_receipt = None
    live_settings = settings or Settings.from_env()
    if require_datahub:
        if not (
            live_settings.datahub_gms_url
            and live_settings.datahub_mcp_url
            and live_settings.datahub_token
        ):
            raise DataHubIntegrationError("DataHub live workflow is not fully configured")
        reader = DataHubMcpReader(
            namespace_prefix=live_settings.datahub_urn_prefix,
            client=StreamableHttpMcpClient(
                url=live_settings.datahub_mcp_url,
                token=live_settings.datahub_token,
            ),
        )
        read_receipt = asyncio.run(
            reader.read_context(
                entrypoint_urns=plan.entrypoint_urns,
                expected_urns=[decision.target_urn for decision in plan.decisions],
            )
        )
    approval = Approval.grant(plan, approver=approver)
    receipts = execute_plan(
        root=root,
        plan=plan,
        approval=approval,
        selector=selector,
        protector=protector,
        artifacts=artifacts,
        selector_secret=selector_secret,
    )
    certificate = verify_and_certify(
        root=root,
        plan=plan,
        selector=selector,
        protector=protector,
        artifacts=artifacts,
        receipts=receipts,
        selector_secret=selector_secret,
    )
    if require_datahub:
        assert read_receipt is not None
        assert live_settings.datahub_gms_url is not None
        assert live_settings.datahub_token is not None
        evidence_dir = root.resolve() / "evidence" / plan.request_id
        (evidence_dir / "datahub-read-receipt.json").write_text(
            read_receipt.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
        graph = create_graph_client(
            gms_url=live_settings.datahub_gms_url,
            token=live_settings.datahub_token,
        )
        write_receipt = write_evidence_properties(
            graph=graph,
            target_urn=CUSTOMERS,
            allowed_targets=plan.entrypoint_urns,
            namespace_prefix=live_settings.datahub_urn_prefix,
            plan=plan,
            certificate=certificate,
        )
        (evidence_dir / "datahub-write-receipt.json").write_text(
            write_receipt.model_dump_json(indent=2) + "\n", encoding="utf-8"
        )
    return certificate


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
    parser.add_argument(
        "--require-datahub",
        action="store_true",
        help="Fail closed unless live MCP context and verified SDK writeback both succeed.",
    )
    args = parser.parse_args()
    certificate = run_workflow(
        root=args.root,
        project_root=args.project_root,
        approver=args.approved_by,
        request_id=args.request_id,
        seed=args.seed,
        require_datahub=args.require_datahub,
        settings=settings,
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
