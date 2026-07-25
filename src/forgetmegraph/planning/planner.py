from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterable

from forgetmegraph.domain.models import (
    ActionPlan,
    ActionType,
    Artifact,
    ArtifactDecision,
    DecisionStatus,
    LineageEdge,
    ProtectedSelector,
)
from forgetmegraph.planning.mappings import MappingRegistry
from forgetmegraph.planning.policy import select_action


class PlanningError(ValueError):
    pass


def build_action_plan(
    *,
    request_id: str,
    selector: ProtectedSelector,
    entrypoint_urns: list[str],
    artifacts: Iterable[Artifact],
    edges: Iterable[LineageEdge],
    mappings: MappingRegistry,
) -> ActionPlan:
    artifact_by_urn = {artifact.urn: artifact for artifact in artifacts}
    adjacency: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adjacency[edge.source_urn].append(edge.destination_urn)

    missing_entrypoints = sorted(set(entrypoint_urns) - artifact_by_urn.keys())
    if missing_entrypoints:
        raise PlanningError(f"unknown entrypoints: {', '.join(missing_entrypoints)}")

    decisions: dict[str, ArtifactDecision] = {}
    queue: deque[tuple[str, str, list[str], bool, str | None]] = deque()
    for urn in entrypoint_urns:
        queue.append((urn, selector.field, [urn], False, None))

    while queue:
        urn, selector_field, path, inherited_block, inherited_reason = queue.popleft()
        artifact = artifact_by_urn.get(urn)
        if artifact is None:
            continue

        if inherited_block:
            decision = ArtifactDecision(
                target_urn=urn,
                artifact_type=artifact.artifact_type,
                action=ActionType.ESCALATE,
                status=DecisionStatus.BLOCKED,
                selector_field=None,
                selector_token=selector.token,
                lineage_path=path,
                reason=inherited_reason or "An upstream selector mapping is unavailable.",
            )
        else:
            action, status, reason = select_action(artifact)
            decision = ArtifactDecision(
                target_urn=urn,
                artifact_type=artifact.artifact_type,
                action=action,
                status=status,
                selector_field=selector_field,
                selector_token=selector.token,
                lineage_path=path,
                reason=reason,
            )

        existing = decisions.get(urn)
        if existing is None or (
            existing.status is DecisionStatus.BLOCKED
            and decision.status is not DecisionStatus.BLOCKED
        ):
            decisions[urn] = decision

        for destination_urn in sorted(adjacency[urn]):
            mapping = mappings.get(urn, selector_field, destination_urn)
            if inherited_block:
                queue.append(
                    (
                        destination_urn,
                        selector_field,
                        [*path, destination_urn],
                        True,
                        inherited_reason,
                    )
                )
            elif mapping is None:
                queue.append(
                    (
                        destination_urn,
                        selector_field,
                        [*path, destination_urn],
                        True,
                        f"Missing selector mapping from {urn} to {destination_urn}; branch fails closed.",  # noqa: E501
                    )
                )
            else:
                queue.append(
                    (
                        destination_urn,
                        mapping.destination_field,
                        [*path, destination_urn],
                        False,
                        None,
                    )
                )

    ordered = sorted(
        decisions.values(),
        key=lambda item: (len(item.lineage_path), item.target_urn),
    )
    return ActionPlan.create(
        request_id=request_id,
        selector_token=selector.token,
        entrypoint_urns=entrypoint_urns,
        decisions=ordered,
    )
