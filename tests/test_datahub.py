import asyncio
import json
from datetime import UTC, datetime
from hashlib import sha256
from importlib.util import find_spec
from pathlib import Path
from types import SimpleNamespace

import pytest

from forgetmegraph.context.datahub import (
    DataHubIntegrationError,
    DataHubMcpReader,
    DataHubReadReceipt,
    DataHubWriteReceipt,
    write_evidence_properties,
)
from forgetmegraph.demo import workflow
from forgetmegraph.demo.seed import inspect_presence, seed_estate
from forgetmegraph.domain.models import ActionPlan
from forgetmegraph.verification.certificate import (
    CertificateStatus,
    EvidenceCertificate,
)

CUSTOMERS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)"
TICKETS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.tickets,PROD)"
SUMMARY = (
    "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.analytics.customer_ticket_summary,PROD)"
)
FEATURES = (
    "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.features.customer_support_profile,PROD)"
)


class FakeMcpClient:
    def __init__(
        self,
        urns: list[str],
        *,
        lineage_urns: list[str] | None = None,
        extra_entity_urn: str | None = None,
    ) -> None:
        self.urns = urns
        self.lineage_urns = lineage_urns or urns
        self.extra_entity_urn = extra_entity_urn
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def list_tools(self) -> list[str]:
        return ["get_lineage", "search", "get_entities"]

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        self.calls.append((name, arguments))
        if name == "get_entities":
            urns = [*self.urns]
            if self.extra_entity_urn:
                urns.append(self.extra_entity_urn)
            return [{"urn": urn, "name": "project asset"} for urn in urns]
        return {
            "searchResults": [{"entity": {"urn": urn}, "degree": 1} for urn in self.lineage_urns]
        }


def test_mcp_read_proves_namespaced_context_without_selector_data() -> None:
    urns = [CUSTOMERS, TICKETS, SUMMARY, FEATURES]
    client = FakeMcpClient(urns)
    reader = DataHubMcpReader(namespace_prefix="forgetme.", client=client)

    receipt = asyncio.run(
        reader.read_context(
            entrypoint_urns=[CUSTOMERS, TICKETS],
            expected_urns=urns,
        )
    )

    assert receipt.entity_urns == sorted(urns)
    assert receipt.lineage_urns == sorted(urns)
    assert len(receipt.entity_response_sha256) == 64
    assert len(receipt.lineage_response_sha256) == 64
    persisted = receipt.model_dump_json()
    arguments = json.dumps(client.calls, sort_keys=True)
    assert "Synthetic Subject" not in persisted
    assert '"42"' not in persisted
    assert '"42"' not in arguments


def test_mcp_read_rejects_cross_namespace_asset() -> None:
    other = "urn:li:dataset:(urn:li:dataPlatform:duckdb,other.raw.customers,PROD)"
    reader = DataHubMcpReader(
        namespace_prefix="forgetme.",
        client=FakeMcpClient([CUSTOMERS], extra_entity_urn=other),
    )

    with pytest.raises(DataHubIntegrationError, match="outside"):
        asyncio.run(
            reader.read_context(
                entrypoint_urns=[CUSTOMERS],
                expected_urns=[CUSTOMERS],
            )
        )


def test_mcp_read_fails_closed_when_lineage_is_incomplete() -> None:
    client = FakeMcpClient(
        [CUSTOMERS, SUMMARY, FEATURES],
        lineage_urns=[CUSTOMERS, SUMMARY],
    )
    reader = DataHubMcpReader(namespace_prefix="forgetme.", client=client)

    with pytest.raises(DataHubIntegrationError, match="lineage is incomplete"):
        asyncio.run(
            reader.read_context(
                entrypoint_urns=[CUSTOMERS],
                expected_urns=[CUSTOMERS, SUMMARY, FEATURES],
            )
        )


def _plan_and_certificate() -> tuple[ActionPlan, EvidenceCertificate]:
    plan = ActionPlan.create(
        request_id="req-datahub-test",
        selector_token="subj_opaque_not_raw",
        entrypoint_urns=[CUSTOMERS],
        decisions=[],
    )
    certificate = EvidenceCertificate(
        request_id=plan.request_id,
        selector_token=plan.selector_token,
        plan_hash=plan.plan_hash,
        generated_at="2026-07-25T00:00:00Z",
        status=CertificateStatus.VERIFIED,
        items=[],
        certificate_hash="c" * 64,
    )
    return plan, certificate


class FakeGraph:
    def __init__(self, properties: dict[str, str]) -> None:
        self.properties = properties
        self.emitted: list[object] = []
        self.rereads = 0

    def test_connection(self) -> None:
        return None

    def emit(self, item: object) -> None:
        self.emitted.append(item)

    def get_aspect(self, entity_urn: str, aspect_type: type[object]) -> object:
        assert entity_urn == CUSTOMERS
        self.rereads += 1
        return SimpleNamespace(customProperties=self.properties)


@pytest.mark.skipif(
    find_spec("datahub") is None,
    reason="SDK writeback proposal test requires the optional datahub dependency group",
)
def test_sdk_writeback_is_allowlisted_reread_and_receipted() -> None:
    plan, certificate = _plan_and_certificate()
    properties = {
        "forgetme.request_sha256": sha256(
            json.dumps(plan.request_id, separators=(",", ":")).encode()
        ).hexdigest(),
        "forgetme.action": "verified_deletion_orchestration",
        "forgetme.status": certificate.status.value,
        "forgetme.plan_sha256": plan.plan_hash,
        "forgetme.certificate_sha256": certificate.certificate_hash,
    }
    graph = FakeGraph(properties)

    receipt = write_evidence_properties(
        graph=graph,
        target_urn=CUSTOMERS,
        allowed_targets=plan.entrypoint_urns,
        namespace_prefix="forgetme.",
        plan=plan,
        certificate=certificate,
    )

    assert graph.emitted
    assert graph.rereads == 1
    assert receipt.verified is True
    assert receipt.expected_properties == receipt.observed_properties
    persisted = receipt.model_dump_json()
    assert "subj_" not in persisted
    assert '"42"' not in persisted


def test_sdk_writeback_rejects_non_allowlisted_target_before_emit() -> None:
    plan, certificate = _plan_and_certificate()
    graph = FakeGraph({})

    with pytest.raises(DataHubIntegrationError, match="not allowlisted"):
        write_evidence_properties(
            graph=graph,
            target_urn=TICKETS,
            allowed_targets=plan.entrypoint_urns,
            namespace_prefix="forgetme.",
            plan=plan,
            certificate=certificate,
        )

    assert graph.emitted == []
    assert graph.rereads == 0


def test_live_workflow_persists_read_and_verified_write_receipts(monkeypatch, tmp_path) -> None:
    class FakeReader:
        def __init__(self, *, namespace_prefix, client) -> None:
            assert namespace_prefix == "forgetme."

        async def read_context(self, *, entrypoint_urns, expected_urns):
            expected = sorted(expected_urns)
            return DataHubReadReceipt(
                generated_at=datetime.now(UTC),
                entrypoint_urns=sorted(entrypoint_urns),
                entity_urns=expected,
                lineage_urns=expected,
                tools=["get_entities", "get_lineage"],
                entity_response_sha256="e" * 64,
                lineage_response_sha256="l" * 64,
            )

    def fake_write(**kwargs):
        certificate = kwargs["certificate"]
        assert (root / "evidence" / certificate.request_id / "certificate.json").is_file()
        return DataHubWriteReceipt(
            generated_at=datetime.now(UTC),
            target_urn=CUSTOMERS,
            operation="datasetProperties.customProperties.patch_and_reread",
            expected_properties={"forgetme.certificate_sha256": certificate.certificate_hash},
            observed_properties={"forgetme.certificate_sha256": certificate.certificate_hash},
            verified=True,
            receipt_sha256="r" * 64,
        )

    monkeypatch.setattr(workflow, "DataHubMcpReader", FakeReader)
    monkeypatch.setattr(workflow, "create_graph_client", lambda **kwargs: object())
    monkeypatch.setattr(workflow, "write_evidence_properties", fake_write)
    settings = SimpleNamespace(
        datahub_gms_url="http://127.0.0.1:8080",
        datahub_mcp_url="http://127.0.0.1:8000/mcp",
        datahub_token=object(),
        datahub_urn_prefix="forgetme.",
    )
    root = tmp_path / "fixtures" / "forget-me-graph"

    certificate = workflow.run_workflow(
        root=root,
        project_root=Path(__file__).parents[1],
        approver="privacy-operator",
        request_id="req-live-workflow-test",
        seed=True,
        require_datahub=True,
        settings=settings,
    )

    evidence = root / "evidence" / certificate.request_id
    read_receipt = (evidence / "datahub-read-receipt.json").read_text()
    write_receipt = (evidence / "datahub-write-receipt.json").read_text()
    assert '"verified": true' in write_receipt
    assert "get_lineage" in read_receipt
    assert "Synthetic Subject" not in read_receipt + write_receipt
    assert '"42"' not in read_receipt + write_receipt


def test_live_workflow_blocks_before_deletion_when_datahub_is_unconfigured(tmp_path) -> None:
    root = tmp_path / "fixtures" / "forget-me-graph"
    before = seed_estate(root)
    settings = SimpleNamespace(
        datahub_gms_url=None,
        datahub_mcp_url=None,
        datahub_token=None,
        datahub_urn_prefix="forgetme.",
    )

    with pytest.raises(DataHubIntegrationError, match="not fully configured"):
        workflow.run_workflow(
            root=root,
            project_root=Path(__file__).parents[1],
            approver="privacy-operator",
            request_id="req-fail-closed-test",
            require_datahub=True,
            settings=settings,
        )

    after = inspect_presence(root, customer_id=6 * 7)
    assert after == before
