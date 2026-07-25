import json
from pathlib import Path

from forgetmegraph.context.provider import FixtureContextProvider
from forgetmegraph.domain.models import (
    ActionType,
    DecisionStatus,
    SelectorMapping,
    SubjectSelector,
)
from forgetmegraph.planning.mappings import MappingRegistry
from forgetmegraph.planning.planner import build_action_plan
from forgetmegraph.privacy.selector import SelectorProtector

ROOT = Path(__file__).parents[1]
CUSTOMERS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)"
TICKETS = "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.tickets,PROD)"
VECTOR = "urn:li:dataset:(urn:li:dataPlatform:vector,forgetme.ticket_embeddings,PROD)"
MODEL = (
    "urn:li:dataset:(urn:li:dataPlatform:mlflow,forgetme.model.customer_support_classifier,PROD)"
)


def _protected_selector():
    return SelectorProtector("a-test-secret-that-is-long-enough").protect(
        SubjectSelector(subject_type="customer", field="customer_id", value="42")
    )


def test_plan_classifies_complete_demo_graph_without_raw_value() -> None:
    context = FixtureContextProvider(ROOT / "demo/metadata/graph.json")
    registry = MappingRegistry.from_json(ROOT / "demo/selector-mappings.json")

    plan = build_action_plan(
        request_id="req-demo-001",
        selector=_protected_selector(),
        entrypoint_urns=[CUSTOMERS, TICKETS],
        artifacts=context.artifacts(),
        edges=context.downstream_edges(),
        mappings=registry,
    )

    by_urn = {item.target_urn: item for item in plan.decisions}
    assert by_urn[VECTOR].action is ActionType.VECTOR_DELETE_REINDEX
    assert by_urn[MODEL].action is ActionType.RETRAIN
    assert by_urn[MODEL].status is DecisionStatus.READY
    assert len(plan.plan_hash) == 64
    assert "42" not in plan.model_dump_json()


def test_missing_mapping_blocks_branch_and_descendants() -> None:
    context = FixtureContextProvider(ROOT / "demo/metadata/graph.json")
    payload = json.loads((ROOT / "demo/selector-mappings.json").read_text(encoding="utf-8"))
    mappings = [
        SelectorMapping.model_validate(item)
        for item in payload["mappings"]
        if item["destination_urn"] != VECTOR
    ]

    plan = build_action_plan(
        request_id="req-demo-002",
        selector=_protected_selector(),
        entrypoint_urns=[CUSTOMERS, TICKETS],
        artifacts=context.artifacts(),
        edges=context.downstream_edges(),
        mappings=MappingRegistry(mappings),
    )

    vector_decision = next(item for item in plan.decisions if item.target_urn == VECTOR)
    assert vector_decision.status is DecisionStatus.BLOCKED
    assert vector_decision.action is ActionType.ESCALATE
    assert "fails closed" in vector_decision.reason
