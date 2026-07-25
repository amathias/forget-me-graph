import asyncio
import json
import subprocess
import sys
from dataclasses import replace
from pathlib import Path

import pytest

from forgetmegraph.config import Settings
from forgetmegraph.context import datahub as datahub_context
from forgetmegraph.context.datahub import DataHubIntegrationError
from forgetmegraph.demo.datahub_catalog import (
    CUSTOMERS,
    DOMAIN_URN,
    EXPECTED_ARTIFACTS,
    EXPECTED_EDGES,
    SUMMARY,
    TAG_URN,
    TICKETS,
    load_catalog_fixture,
    require_catalog_settings,
    seed_datahub_catalog,
    set_catalog_soft_deleted,
    write_catalog_receipt,
)

PROJECT_ROOT = Path(__file__).parents[1]
FIXTURE_PATH = PROJECT_ROOT / "demo/metadata/graph.json"


class FakeCatalogGraph:
    def __init__(self, allowed_urns: set[str]) -> None:
        self.allowed_urns = {*allowed_urns, DOMAIN_URN, TAG_URN}
        self.aspects: dict[tuple[str, type[object]], object] = {}
        self.emitted: list[object] = []
        self.soft_status_calls: list[tuple[str, bool, str]] = []

    def test_connection(self) -> None:
        return None

    def emit(self, item: object) -> None:
        entity_urn = item.entityUrn
        assert entity_urn in self.allowed_urns
        assert item.aspect is not None
        self.emitted.append(item)
        self.aspects[(entity_urn, type(item.aspect))] = item.aspect

    def get_aspect(self, entity_urn: str, aspect_type: type[object]) -> object | None:
        return self.aspects.get((entity_urn, aspect_type))

    def set_soft_delete_status(self, urn: str, delete: bool, run_id: str) -> None:
        from datahub.metadata.schema_classes import StatusClass

        assert urn in self.allowed_urns
        self.soft_status_calls.append((urn, delete, run_id))
        self.aspects[(urn, StatusClass)] = StatusClass(removed=delete)


def _settings() -> Settings:
    return Settings.from_env()


def _fixture():
    return load_catalog_fixture(FIXTURE_PATH, namespace_prefix="forgetme.")


def test_seed_reset_restore_are_exact_idempotent_and_receipted(tmp_path) -> None:
    from datahub.metadata.schema_classes import (
        DatasetPropertiesClass,
        GlobalTagsClass,
        StatusClass,
        TagAssociationClass,
        UpstreamLineageClass,
    )

    fixture = _fixture()
    graph = FakeCatalogGraph(set(fixture.urns))
    graph.aspects[(CUSTOMERS, DatasetPropertiesClass)] = DatasetPropertiesClass(
        customProperties={"forgetme.certificate_sha256": "existing-evidence-hash"}
    )
    graph.aspects[(CUSTOMERS, GlobalTagsClass)] = GlobalTagsClass(
        tags=[TagAssociationClass(tag="urn:li:tag:existing-review-tag")]
    )

    seed_receipt = seed_datahub_catalog(graph, fixture, settings=_settings())

    assert seed_receipt.verified is True
    assert len(seed_receipt.dataset_urns) == 10
    assert seed_receipt.edge_count == 9
    assert seed_receipt.expected_removed is False
    assert set(seed_receipt.verified_aspects) == {
        "datasetProperties",
        "domains",
        "globalTags",
        "status",
        "upstreamLineage",
    }
    customer_properties = graph.get_aspect(CUSTOMERS, DatasetPropertiesClass)
    assert customer_properties.customProperties["forgetme.certificate_sha256"] == (
        "existing-evidence-hash"
    )
    customer_tags = graph.get_aspect(CUSTOMERS, GlobalTagsClass)
    assert {tag.tag for tag in customer_tags.tags} == {
        TAG_URN,
        "urn:li:tag:existing-review-tag",
    }

    observed_edges: set[tuple[str, str]] = set()
    for destination in fixture.urns:
        lineage = graph.get_aspect(destination, UpstreamLineageClass)
        observed_edges.update((upstream.dataset, destination) for upstream in lineage.upstreams)
    assert observed_edges == set(EXPECTED_EDGES)

    repeated = seed_datahub_catalog(graph, fixture, settings=_settings())
    assert repeated.verified is True
    repeated_edges: set[tuple[str, str]] = set()
    for destination in fixture.urns:
        lineage = graph.get_aspect(destination, UpstreamLineageClass)
        repeated_edges.update((upstream.dataset, destination) for upstream in lineage.upstreams)
    assert repeated_edges == set(EXPECTED_EDGES)

    reset_receipt = set_catalog_soft_deleted(graph, fixture, removed=True)
    assert reset_receipt.verified is True
    assert reset_receipt.expected_removed is True
    assert all(reset_receipt.observed_removed.values())
    assert reset_receipt.verified_aspects == ["status"]

    restore_receipt = set_catalog_soft_deleted(graph, fixture, removed=False)
    assert restore_receipt.verified is True
    assert restore_receipt.expected_removed is False
    assert not any(restore_receipt.observed_removed.values())
    assert all(graph.get_aspect(urn, StatusClass).removed is False for urn in fixture.urns)

    receipt_path = write_catalog_receipt(tmp_path / "state", restore_receipt)
    persisted = json.loads(receipt_path.read_text())
    assert persisted["verified"] is True
    assert persisted["operation"] == "restore-datahub"
    serialized = receipt_path.read_text().lower()
    assert "authorization" not in serialized
    assert "bearer" not in serialized
    assert "secret" not in serialized


class FakeReadinessMcpClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def list_tools(self) -> list[str]:
        return ["get_entities", "get_lineage"]

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        self.calls.append((name, arguments))
        if name == "get_entities":
            return [{"urn": urn} for urn in sorted(EXPECTED_ARTIFACTS)]
        return {
            "searchResults": [
                {"entity": {"urn": urn}, "degree": 1} for urn in sorted(EXPECTED_ARTIFACTS)
            ]
        }


def test_readiness_fails_preseed_and_post_reset_then_recovers(monkeypatch) -> None:
    settings = replace(
        _settings(),
        datahub_gms_url="http://127.0.0.1:8080",
        datahub_mcp_url="http://127.0.0.1:8000/mcp",
        datahub_token="test-only-token",
    )
    fixture = _fixture()
    graph = FakeCatalogGraph(set(fixture.urns))
    mcp = FakeReadinessMcpClient()
    monkeypatch.setattr(datahub_context, "create_graph_client", lambda **kwargs: graph)
    monkeypatch.setattr(datahub_context, "StreamableHttpMcpClient", lambda **kwargs: mcp)

    preseed = asyncio.run(datahub_context.probe_datahub(settings))

    assert preseed.ready is False
    assert preseed.catalog == "missing_or_invalid"
    assert preseed.mcp == "unverified"
    assert mcp.calls == []

    seed_datahub_catalog(graph, fixture, settings=settings)
    mutation_counts = (len(graph.emitted), len(graph.soft_status_calls))
    seeded = asyncio.run(datahub_context.probe_datahub(settings))

    assert seeded.ready is True
    assert seeded.catalog == "ready"
    assert seeded.capabilities == ["get_entities", "get_lineage"]
    assert (len(graph.emitted), len(graph.soft_status_calls)) == mutation_counts
    entity_call = next(call for call in mcp.calls if call[0] == "get_entities")
    assert set(entity_call[1]["urns"]) == set(EXPECTED_ARTIFACTS)
    lineage_calls = [call for call in mcp.calls if call[0] == "get_lineage"]
    assert {call[1]["urn"] for call in lineage_calls} == {CUSTOMERS, TICKETS}

    from datahub.metadata.schema_classes import DatasetPropertiesClass, UpstreamLineageClass

    customer_properties = graph.get_aspect(CUSTOMERS, DatasetPropertiesClass)
    graph.aspects[(CUSTOMERS, DatasetPropertiesClass)] = DatasetPropertiesClass(
        name="wrong.fixture.name",
        customProperties=customer_properties.customProperties,
    )
    calls_before_metadata_probe = list(mcp.calls)
    metadata_drift = asyncio.run(datahub_context.probe_datahub(settings))
    assert metadata_drift.ready is False
    assert metadata_drift.catalog == "missing_or_invalid"
    assert mcp.calls == calls_before_metadata_probe

    seed_datahub_catalog(graph, fixture, settings=settings)
    graph.aspects[(SUMMARY, UpstreamLineageClass)] = UpstreamLineageClass(upstreams=[])
    calls_before_lineage_probe = list(mcp.calls)
    lineage_drift = asyncio.run(datahub_context.probe_datahub(settings))
    assert lineage_drift.ready is False
    assert lineage_drift.catalog == "missing_or_invalid"
    assert mcp.calls == calls_before_lineage_probe

    seed_datahub_catalog(graph, fixture, settings=settings)
    reset_receipt = set_catalog_soft_deleted(graph, fixture, removed=True)
    assert reset_receipt.verified is True
    assert len(reset_receipt.observed_removed) == 10
    assert all(reset_receipt.observed_removed.values())
    calls_before_reset_probe = list(mcp.calls)
    reset = asyncio.run(datahub_context.probe_datahub(settings))

    assert reset.ready is False
    assert reset.catalog == "missing_or_invalid"
    assert reset.mcp == "unverified"
    assert mcp.calls == calls_before_reset_probe

    set_catalog_soft_deleted(graph, fixture, removed=False)
    restored = asyncio.run(datahub_context.probe_datahub(settings))

    assert restored.ready is True
    assert restored.catalog == "ready"


def test_catalog_fixture_rejects_foreign_namespace_before_emit(tmp_path) -> None:
    payload = json.loads(FIXTURE_PATH.read_text())
    payload["artifacts"][0]["urn"] = (
        "urn:li:dataset:(urn:li:dataPlatform:duckdb,other.raw.customers,PROD)"
    )
    unsafe_path = tmp_path / "foreign-graph.json"
    unsafe_path.write_text(json.dumps(payload))

    with pytest.raises(DataHubIntegrationError, match="foreign namespace"):
        load_catalog_fixture(unsafe_path, namespace_prefix="forgetme.")


def test_catalog_fixture_rejects_namespaced_nonfixture_target(tmp_path) -> None:
    payload = json.loads(FIXTURE_PATH.read_text())
    payload["artifacts"].append(
        {
            "urn": ("urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.not_allowlisted,PROD)"),
            "name": "not.allowlisted",
            "artifact_type": "unknown",
            "adapter": "none",
        }
    )
    unsafe_path = tmp_path / "extra-graph.json"
    unsafe_path.write_text(json.dumps(payload))

    with pytest.raises(DataHubIntegrationError, match="targets differ"):
        load_catalog_fixture(unsafe_path, namespace_prefix="forgetme.")


def test_soft_reset_rejects_partial_extra_and_empty_target_sets() -> None:
    fixture = _fixture()
    graph = FakeCatalogGraph(set(fixture.urns))
    seed_datahub_catalog(graph, fixture, settings=_settings())
    before = list(graph.soft_status_calls)
    extra = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.not_allowlisted,PROD)"

    with pytest.raises(DataHubIntegrationError, match="targets differ"):
        set_catalog_soft_deleted(
            graph,
            fixture,
            removed=True,
            target_urns=[*fixture.urns, extra],
        )
    with pytest.raises(DataHubIntegrationError, match="targets differ"):
        set_catalog_soft_deleted(
            graph,
            fixture,
            removed=True,
            target_urns=list(fixture.urns)[:-1],
        )
    with pytest.raises(DataHubIntegrationError, match="targets differ"):
        set_catalog_soft_deleted(graph, fixture, removed=True, target_urns=[])

    assert graph.soft_status_calls == before


def test_catalog_module_cli_exposes_guarded_operations() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "forgetmegraph.demo.datahub_catalog", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "seed-datahub" in result.stdout
    assert "reset-datahub" in result.stdout
    assert "restore-datahub" in result.stdout


def test_catalog_settings_reject_contract_drift() -> None:
    unsafe = _settings().__class__(
        **{
            **_settings().__dict__,
            "datahub_urn_prefix": "other.",
        }
    )

    with pytest.raises(DataHubIntegrationError, match="fixed allocation"):
        require_catalog_settings(unsafe)
