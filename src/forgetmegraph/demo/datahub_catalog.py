from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from forgetmegraph.config import Settings
from forgetmegraph.context.datahub import DataHubIntegrationError, create_graph_client
from forgetmegraph.domain.models import Artifact, LineageEdge

PROJECT_SLUG = "forget-me-graph"
NAMESPACE_PREFIX = "forgetme."
PROJECT_TAG = "project-forget-me-graph"
DOMAIN_NAME = "Demo / Forget-Me-Graph"
DOMAIN_URN = "urn:li:domain:forget-me-graph"
TAG_URN = "urn:li:tag:project-forget-me-graph"
FIXTURE_VERSION = "1"

CUSTOMERS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)"
TICKETS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.tickets,PROD)"
SUMMARY = (
    "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.analytics.customer_ticket_summary,PROD)"
)
FEATURES = (
    "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.features.customer_support_profile,PROD)"
)
VECTORS = "urn:li:dataset:(urn:li:dataPlatform:vector,forgetme.ticket_embeddings,PROD)"
CACHE = "urn:li:dataset:(urn:li:dataPlatform:cache,forgetme.customer_summary_cache,PROD)"
EXPORT = "urn:li:dataset:(urn:li:dataPlatform:file,forgetme.customer_support_export,PROD)"
SNAPSHOT = "urn:li:dataset:(urn:li:dataPlatform:file,forgetme.training_snapshot.v1,PROD)"
MODEL = (
    "urn:li:dataset:(urn:li:dataPlatform:mlflow,forgetme.model.customer_support_classifier,PROD)"
)
AGGREGATE = (
    "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.analytics.ticket_category_counts,PROD)"
)

EXPECTED_ARTIFACTS = {
    CUSTOMERS: ("raw.customers", "raw_dataset", "duckdb", "required"),
    TICKETS: ("raw.tickets", "raw_dataset", "duckdb", "required"),
    SUMMARY: (
        "analytics.customer_ticket_summary",
        "derived_dataset",
        "duckdb",
        "required",
    ),
    FEATURES: (
        "features.customer_support_profile",
        "feature_table",
        "duckdb",
        "required",
    ),
    VECTORS: ("vectors.ticket_embeddings", "vector_index", "sqlite_vector", "required"),
    CACHE: ("cache.customer_summary", "cache", "sqlite_cache", "required"),
    EXPORT: ("exports.customer_support.csv", "export", "csv", "required"),
    SNAPSHOT: (
        "training.customer_support.v1",
        "training_snapshot",
        "training_snapshot",
        "required",
    ),
    MODEL: ("model.customer_support_classifier", "ml_model", "sklearn_model", "required"),
    AGGREGATE: (
        "analytics.ticket_category_counts",
        "aggregate",
        "duckdb",
        "exempt",
    ),
}

EXPECTED_EDGES = frozenset(
    {
        (CUSTOMERS, SUMMARY),
        (TICKETS, SUMMARY),
        (TICKETS, VECTORS),
        (TICKETS, AGGREGATE),
        (SUMMARY, FEATURES),
        (SUMMARY, CACHE),
        (SUMMARY, EXPORT),
        (FEATURES, SNAPSHOT),
        (SNAPSHOT, MODEL),
    }
)


class CatalogGraph(Protocol):
    def emit(self, item: object) -> object: ...

    def get_aspect(self, entity_urn: str, aspect_type: type[object]) -> object | None: ...

    def set_soft_delete_status(self, urn: str, delete: bool, run_id: str) -> None: ...


@dataclass(frozen=True)
class CatalogFixture:
    artifacts: tuple[Artifact, ...]
    edges: tuple[LineageEdge, ...]
    fixture_sha256: str

    @property
    def urns(self) -> frozenset[str]:
        return frozenset(artifact.urn for artifact in self.artifacts)


class CatalogLifecycleReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    operation: str
    generated_at: datetime
    fixture_sha256: str
    dataset_urns: list[str]
    edge_count: int
    domain_urn: str
    tag_urn: str
    expected_removed: bool
    observed_removed: dict[str, bool]
    verified_aspects: list[str]
    emitted_operations: int
    verified: bool
    receipt_sha256: str


def catalog_contract_fixture() -> CatalogFixture:
    artifacts = tuple(
        Artifact(
            urn=urn,
            name=metadata[0],
            artifact_type=metadata[1],
            adapter=metadata[2],
            policy=metadata[3],
        )
        for urn, metadata in sorted(EXPECTED_ARTIFACTS.items())
    )
    edges = tuple(
        LineageEdge(source_urn=source, destination_urn=destination)
        for source, destination in sorted(EXPECTED_EDGES)
    )
    payload = {
        "artifacts": [artifact.model_dump(mode="json") for artifact in artifacts],
        "edges": [edge.model_dump(mode="json") for edge in edges],
    }
    return CatalogFixture(
        artifacts=artifacts,
        edges=edges,
        fixture_sha256=_canonical_sha256(payload),
    )


def _canonical_sha256(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def require_catalog_settings(settings: Settings) -> None:
    if (
        settings.project_slug != PROJECT_SLUG
        or settings.datahub_urn_prefix != NAMESPACE_PREFIX
        or settings.datahub_project_tag != PROJECT_TAG
        or settings.datahub_domain != DOMAIN_NAME
    ):
        raise DataHubIntegrationError("DataHub catalog settings differ from the fixed allocation")


def load_catalog_fixture(path: Path, *, namespace_prefix: str) -> CatalogFixture:
    payload = json.loads(path.read_text(encoding="utf-8"))
    artifacts = tuple(Artifact.model_validate(item) for item in payload.get("artifacts", []))
    edges = tuple(LineageEdge.model_validate(item) for item in payload.get("edges", []))
    urns = [artifact.urn for artifact in artifacts]
    if len(urns) != len(set(urns)):
        raise DataHubIntegrationError("DataHub catalog fixture contains duplicate targets")
    if any(not urn.startswith("urn:li:dataset:") or namespace_prefix not in urn for urn in urns):
        raise DataHubIntegrationError("DataHub catalog fixture contains a foreign namespace")
    if set(urns) != set(EXPECTED_ARTIFACTS):
        raise DataHubIntegrationError("DataHub catalog fixture targets differ from the allowlist")

    for artifact in artifacts:
        expected = EXPECTED_ARTIFACTS[artifact.urn]
        observed = (
            artifact.name,
            artifact.artifact_type.value,
            artifact.adapter,
            artifact.policy,
        )
        if observed != expected:
            raise DataHubIntegrationError("DataHub catalog fixture metadata differs from allowlist")

    edge_pairs = [(edge.source_urn, edge.destination_urn) for edge in edges]
    if len(edge_pairs) != len(set(edge_pairs)) or frozenset(edge_pairs) != EXPECTED_EDGES:
        raise DataHubIntegrationError("DataHub catalog fixture lineage differs from the allowlist")
    if any(source not in urns or destination not in urns for source, destination in edge_pairs):
        raise DataHubIntegrationError("DataHub catalog fixture lineage leaves the fixture")

    return CatalogFixture(
        artifacts=artifacts,
        edges=edges,
        fixture_sha256=_canonical_sha256(payload),
    )


def require_exact_targets(target_urns: Iterable[str], fixture: CatalogFixture) -> list[str]:
    requested = set(target_urns)
    if fixture.urns != set(EXPECTED_ARTIFACTS) or requested != fixture.urns:
        raise DataHubIntegrationError("DataHub catalog operation targets differ from the fixture")
    return sorted(requested)


def _get_custom_properties(aspect: object | None) -> dict[str, str]:
    if aspect is None:
        return {}
    if isinstance(aspect, dict):
        return dict(aspect.get("customProperties") or {})
    return dict(getattr(aspect, "customProperties", {}) or {})


def _fixture_properties(artifact: Artifact) -> dict[str, str]:
    return {
        "forgetme.fixture_version": FIXTURE_VERSION,
        "forgetme.project_slug": PROJECT_SLUG,
        "forgetme.artifact_type": artifact.artifact_type.value,
        "forgetme.adapter": artifact.adapter,
        "forgetme.policy": artifact.policy,
    }


def _emit_seed_metadata(
    graph: CatalogGraph,
    fixture: CatalogFixture,
    *,
    settings: Settings,
) -> int:
    from datahub.emitter.mcp import MetadataChangeProposalWrapper
    from datahub.metadata.schema_classes import (
        DatasetLineageTypeClass,
        DatasetPropertiesClass,
        DomainPropertiesClass,
        DomainsClass,
        GlobalTagsClass,
        TagAssociationClass,
        TagPropertiesClass,
        UpstreamClass,
        UpstreamLineageClass,
    )

    emitted = 0
    graph.emit(
        MetadataChangeProposalWrapper(
            entityUrn=DOMAIN_URN,
            aspect=DomainPropertiesClass(
                name=settings.datahub_domain,
                description="Synthetic assets for the Forget-Me-Graph deletion demo.",
                customProperties={"project_slug": settings.project_slug},
            ),
        )
    )
    emitted += 1
    graph.emit(
        MetadataChangeProposalWrapper(
            entityUrn=TAG_URN,
            aspect=TagPropertiesClass(
                name=settings.datahub_project_tag,
                description="Allocated tag for the Forget-Me-Graph hackathon project.",
            ),
        )
    )
    emitted += 1

    upstreams_by_destination: dict[str, list[str]] = defaultdict(list)
    for edge in fixture.edges:
        upstreams_by_destination[edge.destination_urn].append(edge.source_urn)

    for artifact in sorted(fixture.artifacts, key=lambda item: item.urn):
        current_properties = graph.get_aspect(artifact.urn, DatasetPropertiesClass)
        custom_properties = _get_custom_properties(current_properties)
        custom_properties.update(_fixture_properties(artifact))
        graph.emit(
            MetadataChangeProposalWrapper(
                entityUrn=artifact.urn,
                aspect=DatasetPropertiesClass(
                    name=artifact.name,
                    description=(
                        "Synthetic Forget-Me-Graph demo artifact; contains no production data."
                    ),
                    customProperties=custom_properties,
                ),
            )
        )
        emitted += 1

        graph.emit(
            MetadataChangeProposalWrapper(
                entityUrn=artifact.urn,
                aspect=DomainsClass(domains=[DOMAIN_URN]),
            )
        )
        emitted += 1

        existing_tags = graph.get_aspect(artifact.urn, GlobalTagsClass)
        tag_urns = {association.tag for association in (getattr(existing_tags, "tags", None) or [])}
        tag_urns.add(TAG_URN)
        graph.emit(
            MetadataChangeProposalWrapper(
                entityUrn=artifact.urn,
                aspect=GlobalTagsClass(
                    tags=[TagAssociationClass(tag=tag) for tag in sorted(tag_urns)]
                ),
            )
        )
        emitted += 1

        graph.emit(
            MetadataChangeProposalWrapper(
                entityUrn=artifact.urn,
                aspect=UpstreamLineageClass(
                    upstreams=[
                        UpstreamClass(dataset=source, type=DatasetLineageTypeClass.TRANSFORMED)
                        for source in sorted(upstreams_by_destination[artifact.urn])
                    ]
                ),
            )
        )
        emitted += 1
        graph.set_soft_delete_status(
            urn=artifact.urn,
            delete=False,
            run_id="forgetmegraph-catalog-seed",
        )
        emitted += 1
    return emitted


def _verify_catalog(
    graph: CatalogGraph,
    fixture: CatalogFixture,
    *,
    expected_removed: bool,
    require_metadata: bool,
) -> tuple[dict[str, bool], list[str]]:
    from datahub.metadata.schema_classes import (
        DatasetPropertiesClass,
        DomainPropertiesClass,
        DomainsClass,
        GlobalTagsClass,
        StatusClass,
        TagPropertiesClass,
        UpstreamLineageClass,
    )

    observed_removed: dict[str, bool] = {}
    verified_aspects = ["status"]
    upstreams_by_destination: dict[str, set[str]] = defaultdict(set)
    for edge in fixture.edges:
        upstreams_by_destination[edge.destination_urn].add(edge.source_urn)

    if require_metadata:
        domain = graph.get_aspect(DOMAIN_URN, DomainPropertiesClass)
        tag = graph.get_aspect(TAG_URN, TagPropertiesClass)
        domain_properties = _get_custom_properties(domain)
        if (
            getattr(domain, "name", None) != DOMAIN_NAME
            or domain_properties.get("project_slug") != PROJECT_SLUG
            or getattr(tag, "name", None) != PROJECT_TAG
        ):
            raise DataHubIntegrationError("DataHub catalog domain or tag reread did not match")
        verified_aspects.extend(["datasetProperties", "domains", "globalTags", "upstreamLineage"])

    for artifact in fixture.artifacts:
        status = graph.get_aspect(artifact.urn, StatusClass)
        if status is None:
            raise DataHubIntegrationError("DataHub catalog status reread was missing")
        removed = bool(getattr(status, "removed", False))
        observed_removed[artifact.urn] = removed
        if removed is not expected_removed:
            raise DataHubIntegrationError("DataHub catalog status reread did not match")
        if not require_metadata:
            continue

        properties = graph.get_aspect(artifact.urn, DatasetPropertiesClass)
        fixture_properties = _fixture_properties(artifact)
        observed_properties = _get_custom_properties(properties)
        observed_name = (
            properties.get("name")
            if isinstance(properties, dict)
            else getattr(properties, "name", None)
        )
        if observed_name != artifact.name or any(
            observed_properties.get(key) != value for key, value in fixture_properties.items()
        ):
            raise DataHubIntegrationError("DataHub catalog properties reread did not match")

        domains = graph.get_aspect(artifact.urn, DomainsClass)
        if set(getattr(domains, "domains", None) or []) != {DOMAIN_URN}:
            raise DataHubIntegrationError("DataHub catalog domain assignment reread did not match")

        tags = graph.get_aspect(artifact.urn, GlobalTagsClass)
        observed_tags = {association.tag for association in (getattr(tags, "tags", None) or [])}
        if TAG_URN not in observed_tags:
            raise DataHubIntegrationError("DataHub catalog tag assignment reread did not match")

        lineage = graph.get_aspect(artifact.urn, UpstreamLineageClass)
        observed_upstreams = {
            upstream.dataset for upstream in (getattr(lineage, "upstreams", None) or [])
        }
        if observed_upstreams != upstreams_by_destination[artifact.urn]:
            raise DataHubIntegrationError("DataHub catalog lineage reread did not match")

    return dict(sorted(observed_removed.items())), sorted(set(verified_aspects))


def verify_catalog_readiness(
    graph: CatalogGraph,
    *,
    settings: Settings,
) -> tuple[dict[str, bool], list[str]]:
    require_catalog_settings(settings)
    fixture = catalog_contract_fixture()
    require_exact_targets(fixture.urns, fixture)
    return _verify_catalog(
        graph,
        fixture,
        expected_removed=False,
        require_metadata=True,
    )


def _receipt(
    *,
    operation: str,
    fixture: CatalogFixture,
    expected_removed: bool,
    observed_removed: dict[str, bool],
    verified_aspects: list[str],
    emitted_operations: int,
) -> CatalogLifecycleReceipt:
    payload: dict[str, object] = {
        "operation": operation,
        "fixture_sha256": fixture.fixture_sha256,
        "dataset_urns": sorted(fixture.urns),
        "edge_count": len(fixture.edges),
        "domain_urn": DOMAIN_URN,
        "tag_urn": TAG_URN,
        "expected_removed": expected_removed,
        "observed_removed": observed_removed,
        "verified_aspects": verified_aspects,
        "emitted_operations": emitted_operations,
        "verified": True,
    }
    return CatalogLifecycleReceipt(
        generated_at=datetime.now(UTC),
        **payload,
        receipt_sha256=_canonical_sha256(payload),
    )


def seed_datahub_catalog(
    graph: CatalogGraph,
    fixture: CatalogFixture,
    *,
    settings: Settings,
) -> CatalogLifecycleReceipt:
    require_catalog_settings(settings)
    require_exact_targets(fixture.urns, fixture)
    emitted = _emit_seed_metadata(graph, fixture, settings=settings)
    observed, aspects = _verify_catalog(
        graph,
        fixture,
        expected_removed=False,
        require_metadata=True,
    )
    return _receipt(
        operation="seed-datahub",
        fixture=fixture,
        expected_removed=False,
        observed_removed=observed,
        verified_aspects=aspects,
        emitted_operations=emitted,
    )


def set_catalog_soft_deleted(
    graph: CatalogGraph,
    fixture: CatalogFixture,
    *,
    removed: bool,
    target_urns: Iterable[str] | None = None,
) -> CatalogLifecycleReceipt:
    requested_targets = fixture.urns if target_urns is None else target_urns
    targets = require_exact_targets(requested_targets, fixture)
    operation = "reset-datahub" if removed else "restore-datahub"
    for urn in targets:
        graph.set_soft_delete_status(
            urn=urn,
            delete=removed,
            run_id=f"forgetmegraph-catalog-{operation}",
        )
    observed, aspects = _verify_catalog(
        graph,
        fixture,
        expected_removed=removed,
        require_metadata=not removed,
    )
    return _receipt(
        operation=operation,
        fixture=fixture,
        expected_removed=removed,
        observed_removed=observed,
        verified_aspects=aspects,
        emitted_operations=len(targets),
    )


def write_catalog_receipt(state_dir: Path, receipt: CatalogLifecycleReceipt) -> Path:
    receipt_dir = state_dir.resolve() / "datahub-catalog"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    path = receipt_dir / f"{receipt.operation}-receipt.json"
    path.write_text(receipt.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def main() -> None:
    settings = Settings.from_env()
    parser = argparse.ArgumentParser(
        description="Manage the exact allowlisted Forget-Me-Graph DataHub catalog fixture"
    )
    parser.add_argument(
        "operation",
        choices=["seed-datahub", "reset-datahub", "restore-datahub"],
    )
    parser.add_argument(
        "--metadata",
        type=Path,
        default=Path("demo/metadata/graph.json"),
    )
    parser.add_argument("--state-dir", type=Path, default=settings.app_state_dir)
    args = parser.parse_args()

    require_catalog_settings(settings)
    if not settings.datahub_gms_url or not settings.datahub_token:
        raise DataHubIntegrationError("DataHub catalog lifecycle is not fully configured")
    fixture = load_catalog_fixture(args.metadata, namespace_prefix=settings.datahub_urn_prefix)
    graph = create_graph_client(
        gms_url=settings.datahub_gms_url,
        token=settings.datahub_token,
    )
    if args.operation == "seed-datahub":
        receipt = seed_datahub_catalog(graph, fixture, settings=settings)
    else:
        receipt = set_catalog_soft_deleted(
            graph,
            fixture,
            removed=args.operation == "reset-datahub",
        )
    receipt_path = write_catalog_receipt(args.state_dir, receipt)
    print(
        json.dumps(
            {
                "operation": receipt.operation,
                "verified": receipt.verified,
                "dataset_count": len(receipt.dataset_urns),
                "edge_count": receipt.edge_count,
                "receipt_sha256": receipt.receipt_sha256,
                "receipt_path": str(receipt_path),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
