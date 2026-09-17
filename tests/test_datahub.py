import asyncio
import json
import sys
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
    require_namespaced_urns,
    write_evidence_properties,
)
from forgetmegraph.context.namespace import parse_dataset_urn
from forgetmegraph.demo import datahub_catalog, workflow
from forgetmegraph.demo.seed import inspect_presence, seed_estate
from forgetmegraph.domain.models import ActionPlan
from forgetmegraph.execution.safety import SafetyViolation
from forgetmegraph.verification.certificate import (
    CertificateStatus,
    EvidenceCertificate,
    canonical_certificate_payload,
    verify_certificate_file,
)

CUSTOMERS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)"
TICKETS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.tickets,PROD)"
SUMMARY = (
    "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.analytics.customer_ticket_summary,PROD)"
)
FEATURES = (
    "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.features.customer_support_profile,PROD)"
)
NON_DATASET_LINEAGE_ASSET_URNS = [
    "urn:li:chart:(looker,forgetme_customer_pii)",
    "urn:li:dashboard:(superset,forgetme_exec_pii)",
    "urn:li:dataFlow:(airflow,forgetme_export,PROD)",
    "urn:li:dataJob:(urn:li:dataFlow:(airflow,forgetme_export,PROD),copy_pii)",
    "urn:li:mlFeature:(forgetme_features,pii_score)",
    "urn:li:mlFeatureTable:(urn:li:dataPlatform:feast,forgetme_table)",
    "urn:li:mlModel:(urn:li:dataPlatform:mlflow,forgetme.model.shadow,PROD)",
    "urn:li:mlModelGroup:(urn:li:dataPlatform:mlflow,forgetme.group,PROD)",
]


class FakeMcpClient:
    def __init__(
        self,
        urns: list[str],
        *,
        lineage_urns: list[str] | None = None,
        extra_entity_urn: str | None = None,
        metadata_urns: list[str] | None = None,
    ) -> None:
        self.urns = urns
        self.lineage_urns = lineage_urns or urns
        self.extra_entity_urn = extra_entity_urn
        self.metadata_urns = metadata_urns or []
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def list_tools(self) -> list[str]:
        return ["get_lineage", "search", "get_entities"]

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        self.calls.append((name, arguments))
        if name == "get_entities":
            urns = [*self.urns]
            if self.extra_entity_urn:
                urns.append(self.extra_entity_urn)
            return [
                *[{"urn": urn, "name": "project asset"} for urn in urns],
                {"metadata": {"references": [{"urn": urn} for urn in self.metadata_urns]}},
            ]
        return {
            "searchResults": [{"entity": {"urn": urn}, "degree": 1} for urn in self.lineage_urns],
            "metadata": {"references": [{"urn": urn} for urn in self.metadata_urns]},
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


def test_mcp_read_rejects_unplanned_in_namespace_entity() -> None:
    extra = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.copy,PROD)"
    reader = DataHubMcpReader(
        namespace_prefix="forgetme.",
        client=FakeMcpClient([CUSTOMERS], extra_entity_urn=extra),
    )

    with pytest.raises(DataHubIntegrationError, match="unplanned assets"):
        asyncio.run(
            reader.read_context(
                entrypoint_urns=[CUSTOMERS],
                expected_urns=[CUSTOMERS],
            )
        )


def test_mcp_read_rejects_unplanned_in_namespace_lineage_descendant() -> None:
    extra = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.analytics.copy,PROD)"
    reader = DataHubMcpReader(
        namespace_prefix="forgetme.",
        client=FakeMcpClient([CUSTOMERS], lineage_urns=[CUSTOMERS, extra]),
    )

    with pytest.raises(DataHubIntegrationError, match="lineage contains unplanned assets"):
        asyncio.run(
            reader.read_context(
                entrypoint_urns=[CUSTOMERS],
                expected_urns=[CUSTOMERS],
            )
        )


@pytest.mark.parametrize("extra", NON_DATASET_LINEAGE_ASSET_URNS)
def test_mcp_read_rejects_unplanned_non_dataset_lineage_descendant(extra: str) -> None:
    reader = DataHubMcpReader(
        namespace_prefix="forgetme.",
        client=FakeMcpClient([CUSTOMERS], lineage_urns=[CUSTOMERS, extra]),
    )

    with pytest.raises(DataHubIntegrationError, match="unsupported or malformed"):
        asyncio.run(
            reader.read_context(
                entrypoint_urns=[CUSTOMERS],
                expected_urns=[CUSTOMERS],
            )
        )


def test_mcp_read_ignores_non_asset_metadata_urns() -> None:
    metadata_urns = [
        "urn:li:dataPlatform:duckdb",
        "urn:li:corpuser:privacy-operator",
        "urn:li:tag:pii",
        "urn:li:glossaryTerm:personal-data",
        "urn:li:domain:privacy",
    ]
    reader = DataHubMcpReader(
        namespace_prefix="forgetme.",
        client=FakeMcpClient([CUSTOMERS], metadata_urns=metadata_urns),
    )

    receipt = asyncio.run(
        reader.read_context(
            entrypoint_urns=[CUSTOMERS],
            expected_urns=[CUSTOMERS],
        )
    )

    assert receipt.entity_urns == [CUSTOMERS]
    assert receipt.lineage_urns == [CUSTOMERS]


def test_mcp_read_fails_closed_when_entity_context_is_incomplete() -> None:
    reader = DataHubMcpReader(
        namespace_prefix="forgetme.",
        client=FakeMcpClient([CUSTOMERS]),
    )

    with pytest.raises(DataHubIntegrationError, match="entity context is incomplete"):
        asyncio.run(
            reader.read_context(
                entrypoint_urns=[CUSTOMERS],
                expected_urns=[CUSTOMERS, TICKETS],
            )
        )


def test_mcp_read_rejects_malformed_dataset_urn() -> None:
    malformed = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw,copy,PROD)"
    reader = DataHubMcpReader(
        namespace_prefix="forgetme.",
        client=FakeMcpClient([CUSTOMERS], extra_entity_urn=malformed),
    )

    with pytest.raises(DataHubIntegrationError, match="unsupported or malformed"):
        asyncio.run(
            reader.read_context(
                entrypoint_urns=[CUSTOMERS],
                expected_urns=[CUSTOMERS],
            )
        )


def test_namespace_validation_rejects_embedded_prefix_and_malformed_urns() -> None:
    embedded = "urn:li:dataset:(urn:li:dataPlatform:forgetme.duckdb,other.raw.data,PROD)"
    malformed = "urn:li:dataset:forgetme.raw.customers"

    for urn in (embedded, malformed):
        with pytest.raises(DataHubIntegrationError):
            require_namespaced_urns([urn], "forgetme.")

    parsed = parse_dataset_urn(CUSTOMERS)
    assert parsed.name == "forgetme.raw.customers"

    bare_prefix = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.,PROD)"
    with pytest.raises(DataHubIntegrationError):
        require_namespaced_urns([bare_prefix], "forgetme.")


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
        confirmed_by="privacy-operator",
        request_id="req-live-workflow-test",
        seed=True,
        require_datahub=True,
        settings=settings,
    )

    evidence = root / "evidence" / certificate.request_id
    read_receipt = (evidence / "datahub-read-receipt.json").read_text()
    write_receipt = (evidence / "datahub-write-receipt.json").read_text()
    read_payload = DataHubReadReceipt.model_validate_json(read_receipt)
    assert '"verified": true' in write_receipt
    assert "get_lineage" in read_receipt
    assert read_payload.request_id == certificate.request_id
    assert read_payload.plan_hash == certificate.plan_hash
    assert read_payload.receipt_sha256 == certificate.datahub_read_receipt_sha256
    assert (
        json.loads(canonical_certificate_payload(certificate))["hash_schema"]
        == "forgetme-certificate-v2"
    )
    assert read_payload.verifies_binding(
        request_id=certificate.request_id,
        plan_hash=certificate.plan_hash,
        receipt_sha256=certificate.datahub_read_receipt_sha256 or "",
    )
    assert not read_payload.verifies_binding(
        request_id="req-different-request",
        plan_hash=certificate.plan_hash,
        receipt_sha256=certificate.datahub_read_receipt_sha256 or "",
    )
    assert "Synthetic Subject" not in read_receipt + write_receipt
    assert '"42"' not in read_receipt + write_receipt

    certificate_path = evidence / "certificate.json"
    assert verify_certificate_file(certificate_path) == certificate
    copied_receipt = read_payload.bind(
        request_id="req-different-request",
        plan_hash=certificate.plan_hash,
    )
    (evidence / "datahub-read-receipt.json").write_text(
        copied_receipt.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="binding verification failed"):
        verify_certificate_file(certificate_path)


def test_live_read_receipt_is_persisted_before_execution(monkeypatch, tmp_path) -> None:
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

    root = tmp_path / "fixtures" / "forget-me-graph"

    def fail_during_execution(**kwargs):
        plan = kwargs["plan"]
        path = root / "evidence" / plan.request_id / "datahub-read-receipt.json"
        receipt = DataHubReadReceipt.model_validate_json(path.read_text(encoding="utf-8"))
        assert receipt.verifies_binding(
            request_id=plan.request_id,
            plan_hash=plan.plan_hash,
            receipt_sha256=receipt.receipt_sha256 or "",
        )
        raise RuntimeError("forced execution boundary failure")

    monkeypatch.setattr(workflow, "DataHubMcpReader", FakeReader)
    monkeypatch.setattr(workflow, "execute_plan", fail_during_execution)
    settings = SimpleNamespace(
        datahub_gms_url="http://127.0.0.1:8080",
        datahub_mcp_url="http://127.0.0.1:8000/mcp",
        datahub_token=object(),
        datahub_urn_prefix="forgetme.",
    )

    with pytest.raises(RuntimeError, match="forced execution boundary failure"):
        workflow.run_workflow(
            root=root,
            project_root=Path(__file__).parents[1],
            confirmed_by="privacy-operator",
            request_id="req-read-before-execution",
            seed=True,
            require_datahub=True,
            settings=settings,
        )

    assert (root / "evidence/req-read-before-execution/datahub-read-receipt.json").is_file()


def test_live_read_receipt_is_not_written_without_fixture_marker(monkeypatch, tmp_path) -> None:
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

    monkeypatch.setattr(workflow, "DataHubMcpReader", FakeReader)
    settings = SimpleNamespace(
        datahub_gms_url="http://127.0.0.1:8080",
        datahub_mcp_url="http://127.0.0.1:8000/mcp",
        datahub_token=object(),
        datahub_urn_prefix="forgetme.",
    )
    root = tmp_path / "unmarked"

    with pytest.raises(SafetyViolation, match="marked demo fixture"):
        workflow.run_workflow(
            root=root,
            project_root=Path(__file__).parents[1],
            confirmed_by="privacy-operator",
            request_id="req-unmarked-read-receipt",
            require_datahub=True,
            settings=settings,
        )

    assert not (root / "evidence").exists()


@pytest.mark.parametrize(
    ("entrypoint", "program"),
    [
        (workflow.main, "forgetmegraph-workflow"),
        (datahub_catalog.main, "forgetmegraph-datahub"),
    ],
)
def test_cli_help_does_not_require_app_env(monkeypatch, capsys, entrypoint, program) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setattr(sys, "argv", [program, "--help"])

    with pytest.raises(SystemExit) as exc_info:
        entrypoint()

    assert exc_info.value.code == 0
    assert "usage:" in capsys.readouterr().out


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
            confirmed_by="privacy-operator",
            request_id="req-fail-closed-test",
            require_datahub=True,
            settings=settings,
        )

    after = inspect_presence(root, customer_id=6 * 7)
    assert after == before


def test_live_workflow_checks_datahub_before_fixture_reset(tmp_path) -> None:
    root = tmp_path / "fixtures" / "forget-me-graph"
    before = seed_estate(root)
    sentinel = root / "evidence" / "prior-request" / "sentinel.txt"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("prior evidence", encoding="utf-8")
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
            confirmed_by="privacy-operator",
            request_id="req-gate-before-reset",
            seed=True,
            require_datahub=True,
            settings=settings,
        )

    assert inspect_presence(root, customer_id=6 * 7) == before
    assert sentinel.read_text(encoding="utf-8") == "prior evidence"


@pytest.mark.parametrize(
    ("extra", "error_pattern"),
    [
        (
            "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.analytics.copy,PROD)",
            "lineage contains unplanned assets",
        ),
        (
            "urn:li:chart:(looker,forgetme_customer_pii)",
            "unsupported or malformed",
        ),
    ],
)
def test_live_workflow_blocks_unplanned_descendant_before_fixture_reset(
    monkeypatch,
    tmp_path,
    extra: str,
    error_pattern: str,
) -> None:
    project_root = Path(__file__).parents[1]
    expected = sorted(
        decision.target_urn
        for decision in workflow.prepare_demo_workflow(
            project_root=project_root,
            request_id="req-unplanned-descendant",
            selector_value="42",
            selector_secret="demo-secret-at-least-16-chars",
        ).plan.decisions
    )
    client = FakeMcpClient(expected, lineage_urns=[*expected, extra])
    monkeypatch.setattr(workflow, "StreamableHttpMcpClient", lambda **kwargs: client)
    settings = SimpleNamespace(
        datahub_gms_url="http://127.0.0.1:8080",
        datahub_mcp_url="http://127.0.0.1:8000/mcp",
        datahub_token=object(),
        datahub_urn_prefix="forgetme.",
    )
    root = tmp_path / "fixtures" / "forget-me-graph"
    before = seed_estate(root)
    sentinel = root / "evidence" / "prior-request" / "sentinel.txt"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_text("prior evidence", encoding="utf-8")

    with pytest.raises(DataHubIntegrationError, match=error_pattern):
        workflow.run_workflow(
            root=root,
            project_root=project_root,
            confirmed_by="privacy-operator",
            request_id="req-unplanned-descendant",
            selector_secret="demo-secret-at-least-16-chars",
            seed=True,
            require_datahub=True,
            settings=settings,
        )

    assert inspect_presence(root, customer_id=6 * 7) == before
    assert sentinel.read_text(encoding="utf-8") == "prior evidence"
