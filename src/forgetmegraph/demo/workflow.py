from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
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
from forgetmegraph.domain.models import ActionPlan, Artifact, ProtectedSelector, SubjectSelector
from forgetmegraph.execution.engine import execute_plan
from forgetmegraph.execution.models import PlanConfirmation
from forgetmegraph.execution.safety import require_fixture_marker
from forgetmegraph.planning.mappings import MappingRegistry
from forgetmegraph.planning.planner import build_action_plan
from forgetmegraph.privacy.selector import SelectorProtector
from forgetmegraph.verification.certificate import EvidenceCertificate, verify_and_certify

CUSTOMERS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)"
TICKETS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.tickets,PROD)"


@dataclass(frozen=True)
class PreparedDemoWorkflow:
    plan: ActionPlan
    selector: ProtectedSelector
    artifacts: tuple[Artifact, ...]


def prepare_demo_workflow(
    *,
    project_root: Path,
    request_id: str,
    selector_value: str,
    selector_secret: str = DEMO_SECRET,
) -> PreparedDemoWorkflow:
    context = FixtureContextProvider(project_root / "demo/metadata/graph.json")
    artifacts = tuple(context.artifacts())
    mappings = MappingRegistry.from_json(project_root / "demo/selector-mappings.json")
    protector = SelectorProtector(selector_secret)
    selector = protector.protect(
        SubjectSelector(subject_type="customer", field="customer_id", value=selector_value)
    )
    plan = build_action_plan(
        request_id=request_id,
        selector=selector,
        entrypoint_urns=[CUSTOMERS, TICKETS],
        artifacts=artifacts,
        edges=context.downstream_edges(),
        mappings=mappings,
    )
    return PreparedDemoWorkflow(plan=plan, selector=selector, artifacts=artifacts)


def run_workflow(
    *,
    root: Path,
    project_root: Path,
    confirmed_by: str,
    request_id: str = "req-demo-001",
    selector_value: str = "42",
    selector_secret: str = DEMO_SECRET,
    expected_plan_hash: str | None = None,
    seed: bool = False,
    require_datahub: bool = False,
    settings: Settings | None = None,
) -> EvidenceCertificate:
    prepared = prepare_demo_workflow(
        project_root=project_root,
        request_id=request_id,
        selector_value=selector_value,
        selector_secret=selector_secret,
    )
    plan = prepared.plan
    selector = prepared.selector
    artifacts = prepared.artifacts
    protector = SelectorProtector(selector_secret)
    if expected_plan_hash is not None and expected_plan_hash != plan.plan_hash:
        raise ValueError("confirmed plan hash does not match the current deterministic plan")
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
        read_receipt = read_receipt.bind(
            request_id=plan.request_id,
            plan_hash=plan.plan_hash,
        )
    if seed:
        seed_estate(root, selector_secret=selector_secret)
    if read_receipt is not None:
        verified_root = require_fixture_marker(root)
        evidence_dir = verified_root / "evidence" / plan.request_id
        evidence_dir.mkdir(parents=True, exist_ok=True)
        read_path = evidence_dir / "datahub-read-receipt.json"
        read_temporary = read_path.with_suffix(".tmp")
        read_temporary.write_text(
            read_receipt.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(read_temporary, read_path)
    confirmation = PlanConfirmation.grant(plan, confirmed_by=confirmed_by)
    receipts = execute_plan(
        root=root,
        plan=plan,
        confirmation=confirmation,
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
        datahub_read_receipt_sha256=(
            read_receipt.receipt_sha256 if read_receipt is not None else None
        ),
    )
    if require_datahub:
        assert read_receipt is not None
        assert live_settings.datahub_gms_url is not None
        assert live_settings.datahub_token is not None
        evidence_dir = root.resolve() / "evidence" / plan.request_id
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
    parser = argparse.ArgumentParser(
        description="Run the plan-confirmation-gated synthetic deletion and retraining workflow"
    )
    parser.add_argument(
        "--confirmed-by",
        "--approved-by",
        dest="confirmed_by",
        required=True,
        help="Operator confirming the exact deterministic plan hash.",
    )
    parser.add_argument("--request-id", default="req-demo-001")
    parser.add_argument("--root", type=Path)
    parser.add_argument("--project-root", type=Path, default=Path("."))
    parser.add_argument("--seed", action="store_true")
    parser.add_argument(
        "--require-datahub",
        action="store_true",
        help="Fail closed unless live MCP context and verified SDK writeback both succeed.",
    )
    args = parser.parse_args()
    settings = Settings.from_env()
    selector_secret = settings.selector_secret
    if selector_secret is None:
        if settings.app_env not in {"local", "test"}:
            parser.error("FMG_SELECTOR_SECRET is required outside local/test mode")
        selector_secret = DEMO_SECRET
    certificate = run_workflow(
        root=args.root or settings.demo_fixture_root,
        project_root=args.project_root,
        confirmed_by=args.confirmed_by,
        request_id=args.request_id,
        selector_secret=selector_secret,
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
