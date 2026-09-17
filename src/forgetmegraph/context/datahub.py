from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from forgetmegraph.config import Settings
from forgetmegraph.context.namespace import dataset_urn_is_namespaced
from forgetmegraph.domain.models import ActionPlan
from forgetmegraph.errors import IntegrationFailure
from forgetmegraph.verification.certificate import EvidenceCertificate

REQUIRED_MCP_TOOLS = frozenset({"get_entities", "get_lineage"})
DATASET_URN_PREFIX = "urn:li:dataset:"
_LINEAGE_ASSET_URN_PREFIXES = (
    DATASET_URN_PREFIX,
    "urn:li:chart:",
    "urn:li:dashboard:",
    "urn:li:dataFlow:",
    "urn:li:dataJob:",
    "urn:li:mlFeature:",
    "urn:li:mlFeatureTable:",
    "urn:li:mlModel:",
    "urn:li:mlModelGroup:",
)
WRITE_PROPERTY_PREFIX = "forgetme."


class DataHubIntegrationError(IntegrationFailure):
    """Privacy-safe integration failure; messages never contain credentials or selectors."""


class McpToolClient(Protocol):
    async def list_tools(self) -> list[str]: ...

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object: ...


class GraphClient(Protocol):
    def test_connection(self) -> None: ...

    def emit(self, item: object) -> object: ...

    def get_aspect(self, entity_urn: str, aspect_type: type[object]) -> object | None: ...


class DataHubReadReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str | None = None
    request_id: str | None = None
    plan_hash: str | None = None
    generated_at: datetime
    entrypoint_urns: list[str]
    entity_urns: list[str]
    lineage_urns: list[str]
    tools: list[str]
    entity_response_sha256: str
    lineage_response_sha256: str
    context_sha256: str | None = None
    receipt_sha256: str | None = None

    def bind(self, *, request_id: str, plan_hash: str) -> DataHubReadReceipt:
        context_payload = {
            "entrypoint_urns": self.entrypoint_urns,
            "entity_urns": self.entity_urns,
            "lineage_urns": self.lineage_urns,
            "tools": self.tools,
            "entity_response_sha256": self.entity_response_sha256,
            "lineage_response_sha256": self.lineage_response_sha256,
        }
        bound = self.model_copy(
            update={
                "schema_version": "forgetme-datahub-read-receipt-v2",
                "request_id": request_id,
                "plan_hash": plan_hash,
                "context_sha256": _canonical_sha256(context_payload),
                "receipt_sha256": None,
            }
        )
        receipt_hash = _canonical_sha256(bound.model_dump(mode="json", exclude={"receipt_sha256"}))
        return bound.model_copy(update={"receipt_sha256": receipt_hash})

    def verifies_binding(
        self,
        *,
        request_id: str,
        plan_hash: str,
        receipt_sha256: str,
    ) -> bool:
        if (
            self.schema_version != "forgetme-datahub-read-receipt-v2"
            or self.request_id != request_id
            or self.plan_hash != plan_hash
            or self.receipt_sha256 != receipt_sha256
        ):
            return False
        unbound = self.model_copy(
            update={
                "schema_version": None,
                "request_id": None,
                "plan_hash": None,
                "context_sha256": None,
                "receipt_sha256": None,
            }
        )
        return unbound.bind(request_id=request_id, plan_hash=plan_hash) == self


class DataHubWriteReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    generated_at: datetime
    target_urn: str
    operation: str
    expected_properties: dict[str, str]
    observed_properties: dict[str, str]
    verified: bool
    receipt_sha256: str


class DataHubCapabilityStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ready: bool
    gms: str
    mcp: str
    catalog: str
    capabilities: list[str]
    blocker: str | None = None


def _canonical_sha256(value: object) -> str:
    return sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def _object_payload(value: object) -> object:
    if isinstance(value, (dict, list, str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump(mode="json", exclude_none=True)  # type: ignore[attr-defined]
        structured = dumped.get("structuredContent")
        if structured is not None:
            return structured
        content = dumped.get("content", [])
        texts = [
            item.get("text") for item in content if isinstance(item, dict) and item.get("text")
        ]
        if texts:
            try:
                return json.loads(texts[0])
            except json.JSONDecodeError:
                return {"text": texts[0]}
        return dumped
    raise DataHubIntegrationError("MCP returned an unsupported response type")


def _asset_urns(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for child in value.values():
            found.update(_asset_urns(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_asset_urns(child))
    elif isinstance(value, str) and value.startswith(_LINEAGE_ASSET_URN_PREFIXES):
        found.add(value)
    return found


def require_namespaced_urns(urns: Iterable[str], prefix: str) -> set[str]:
    urn_set = set(urns)
    try:
        outside = sorted(urn for urn in urn_set if not dataset_urn_is_namespaced(urn, prefix))
    except ValueError as exc:
        raise DataHubIntegrationError(
            "DataHub returned an unsupported or malformed asset URN"
        ) from exc
    if outside:
        raise DataHubIntegrationError(
            "DataHub returned assets outside the allocated project namespace"
        )
    return urn_set


class DataHubMcpReader:
    def __init__(self, *, namespace_prefix: str, client: McpToolClient) -> None:
        self._namespace_prefix = namespace_prefix
        self._client = client

    async def read_context(
        self,
        *,
        entrypoint_urns: list[str],
        expected_urns: Iterable[str],
    ) -> DataHubReadReceipt:
        expected = require_namespaced_urns(expected_urns, self._namespace_prefix)
        entrypoints = require_namespaced_urns(entrypoint_urns, self._namespace_prefix)
        tools = sorted(await self._client.list_tools())
        if REQUIRED_MCP_TOOLS - set(tools):
            raise DataHubIntegrationError("DataHub MCP lacks required read capabilities")

        entity_raw = await self._client.call_tool("get_entities", {"urns": sorted(expected)})
        entity_payload = _object_payload(entity_raw)
        entity_urns = require_namespaced_urns(_asset_urns(entity_payload), self._namespace_prefix)
        missing_entities = expected - entity_urns
        unexpected_entities = entity_urns - expected
        if missing_entities:
            raise DataHubIntegrationError(
                "DataHub entity context is incomplete for the action scope"
            )
        if unexpected_entities:
            raise DataHubIntegrationError("DataHub entity context contains unplanned assets")

        lineage_payloads: list[object] = []
        lineage_urns = set(entrypoints)
        for urn in sorted(entrypoints):
            raw = await self._client.call_tool(
                "get_lineage",
                {
                    "urn": urn,
                    "upstream": False,
                    "max_hops": 3,
                    "max_results": 100,
                },
            )
            payload = _object_payload(raw)
            lineage_payloads.append(payload)
            lineage_urns.update(
                require_namespaced_urns(_asset_urns(payload), self._namespace_prefix)
            )
        missing_lineage = expected - lineage_urns
        unexpected_lineage = lineage_urns - expected
        if missing_lineage:
            raise DataHubIntegrationError("DataHub lineage is incomplete for the action scope")
        if unexpected_lineage:
            raise DataHubIntegrationError("DataHub lineage contains unplanned assets")

        return DataHubReadReceipt(
            generated_at=datetime.now(UTC),
            entrypoint_urns=sorted(entrypoints),
            entity_urns=sorted(entity_urns),
            lineage_urns=sorted(lineage_urns),
            tools=tools,
            entity_response_sha256=_canonical_sha256(entity_payload),
            lineage_response_sha256=_canonical_sha256(lineage_payloads),
        )


class StreamableHttpMcpClient:
    def __init__(self, *, url: str, token: str, timeout_seconds: float = 10.0) -> None:
        self._url = url
        self._token = token
        self._timeout_seconds = timeout_seconds

    def _connect(self):  # type: ignore[no-untyped-def]
        import httpx
        from mcp import ClientSession
        from mcp.client.streamable_http import streamable_http_client

        headers = {"Authorization": f"Bearer {self._token}"}
        http_client = httpx.AsyncClient(headers=headers, timeout=self._timeout_seconds)
        streams = streamable_http_client(self._url, http_client=http_client)
        return ClientSession, http_client, streams

    async def list_tools(self) -> list[str]:
        client_session, http_client, streams = self._connect()
        async with http_client, streams as (read_stream, write_stream, _):
            async with client_session(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()
                return [tool.name for tool in result.tools]

    async def call_tool(self, name: str, arguments: dict[str, object]) -> object:
        client_session, http_client, streams = self._connect()
        async with http_client, streams as (read_stream, write_stream, _):
            async with client_session(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(name, arguments)
                if result.isError:
                    raise DataHubIntegrationError("DataHub MCP tool call failed")
                return result


def create_graph_client(*, gms_url: str, token: str) -> GraphClient:
    from datahub.ingestion.graph.client import DataHubGraph, DataHubGraphConfig

    return DataHubGraph(DataHubGraphConfig(server=gms_url, token=token, timeout_sec=10))


def write_evidence_properties(
    *,
    graph: GraphClient,
    target_urn: str,
    allowed_targets: Iterable[str],
    namespace_prefix: str,
    plan: ActionPlan,
    certificate: EvidenceCertificate,
) -> DataHubWriteReceipt:
    allowed = require_namespaced_urns(allowed_targets, namespace_prefix)
    require_namespaced_urns([target_urn], namespace_prefix)
    if target_urn not in allowed:
        raise DataHubIntegrationError("DataHub write target is not allowlisted by the action plan")

    from datahub.metadata.schema_classes import DatasetPropertiesClass
    from datahub.specific.dataset import DatasetPatchBuilder

    properties = {
        f"{WRITE_PROPERTY_PREFIX}request_sha256": _canonical_sha256(plan.request_id),
        f"{WRITE_PROPERTY_PREFIX}action": "verified_deletion_orchestration",
        f"{WRITE_PROPERTY_PREFIX}status": certificate.status.value,
        f"{WRITE_PROPERTY_PREFIX}plan_sha256": plan.plan_hash,
        f"{WRITE_PROPERTY_PREFIX}certificate_sha256": certificate.certificate_hash,
    }
    builder = DatasetPatchBuilder(target_urn)
    for key, value in sorted(properties.items()):
        builder.add_custom_property(key, value)
    for proposal in builder.build():
        graph.emit(proposal)

    aspect = graph.get_aspect(target_urn, DatasetPropertiesClass)
    if aspect is None:
        observed: dict[str, str] = {}
    elif isinstance(aspect, dict):
        observed = dict(aspect.get("customProperties") or {})
    else:
        observed = dict(getattr(aspect, "customProperties", {}) or {})
    observed_receipt = {key: observed.get(key, "") for key in properties}
    verified = observed_receipt == properties
    receipt_payload = {
        "target_urn": target_urn,
        "operation": "datasetProperties.customProperties.patch_and_reread",
        "expected_properties": properties,
        "observed_properties": observed_receipt,
        "verified": verified,
    }
    receipt = DataHubWriteReceipt(
        generated_at=datetime.now(UTC),
        **receipt_payload,
        receipt_sha256=_canonical_sha256(receipt_payload),
    )
    if not verified:
        raise DataHubIntegrationError("DataHub writeback could not be verified by immediate reread")
    return receipt


async def probe_datahub(settings: Settings) -> DataHubCapabilityStatus:
    if not settings.datahub_gms_url or not settings.datahub_mcp_url or not settings.datahub_token:
        return DataHubCapabilityStatus(
            ready=False,
            gms="unconfigured",
            mcp="unconfigured",
            catalog="unverified",
            capabilities=[],
            blocker="DataHub connection is not fully configured",
        )
    try:
        graph = create_graph_client(gms_url=settings.datahub_gms_url, token=settings.datahub_token)
        await asyncio.to_thread(graph.test_connection)
    except Exception:
        return DataHubCapabilityStatus(
            ready=False,
            gms="unreachable",
            mcp="unverified",
            catalog="unverified",
            capabilities=[],
            blocker="DataHub GMS connectivity probe failed",
        )

    try:
        from forgetmegraph.demo.datahub_catalog import (
            CUSTOMERS,
            EXPECTED_ARTIFACTS,
            TICKETS,
            verify_catalog_readiness,
        )

        await asyncio.to_thread(verify_catalog_readiness, graph, settings=settings)
    except Exception:
        return DataHubCapabilityStatus(
            ready=False,
            gms="connected",
            mcp="unverified",
            catalog="missing_or_invalid",
            capabilities=[],
            blocker="DataHub catalog allocation is not seeded or valid",
        )

    try:
        reader = DataHubMcpReader(
            namespace_prefix=settings.datahub_urn_prefix,
            client=StreamableHttpMcpClient(
                url=settings.datahub_mcp_url,
                token=settings.datahub_token,
            ),
        )
        receipt = await reader.read_context(
            entrypoint_urns=[CUSTOMERS, TICKETS],
            expected_urns=EXPECTED_ARTIFACTS,
        )
    except Exception:
        return DataHubCapabilityStatus(
            ready=False,
            gms="connected",
            mcp="unreachable_or_incapable",
            catalog="ready",
            capabilities=[],
            blocker="DataHub MCP connectivity, capability, or exact lineage probe failed",
        )
    return DataHubCapabilityStatus(
        ready=True,
        gms="connected",
        mcp="connected",
        catalog="ready",
        capabilities=sorted(set(receipt.tools) & REQUIRED_MCP_TOOLS),
    )
