from pathlib import Path

from forgetmegraph.context.namespace import dataset_urn_is_namespaced
from forgetmegraph.demo.seed import MARKER
from forgetmegraph.domain.models import ActionPlan
from forgetmegraph.errors import PolicyViolation
from forgetmegraph.execution.models import PlanConfirmation


class SafetyViolation(PolicyViolation):
    pass


def require_plan_confirmation(plan: ActionPlan, confirmation: PlanConfirmation) -> None:
    if confirmation.request_id != plan.request_id:
        raise SafetyViolation("plan confirmation request does not match action plan")
    if confirmation.plan_hash != plan.plan_hash:
        raise SafetyViolation("plan confirmation is stale because the action plan changed")


def require_fixture_marker(root: Path) -> Path:
    resolved = root.resolve()
    marker = resolved / MARKER
    if not marker.is_file():
        raise SafetyViolation("destructive execution requires a marked demo fixture root")
    if resolved == Path(resolved.anchor) or resolved == Path.cwd().resolve():
        raise SafetyViolation("refusing to execute against a broad filesystem target")
    return resolved


def require_namespace(plan: ActionPlan, prefix: str) -> None:
    invalid: list[str] = []
    for decision in plan.decisions:
        try:
            in_namespace = dataset_urn_is_namespaced(decision.target_urn, prefix)
        except ValueError:
            in_namespace = False
        if not in_namespace:
            invalid.append(decision.target_urn)
    invalid.sort()
    if invalid:
        raise SafetyViolation(
            "action plan contains targets outside the allocated DataHub namespace: "
            + ", ".join(invalid)
        )
