from pathlib import Path

from forgetmegraph.demo.seed import MARKER
from forgetmegraph.domain.models import ActionPlan
from forgetmegraph.execution.models import Approval


class SafetyViolation(ValueError):
    pass


def require_approval(plan: ActionPlan, approval: Approval) -> None:
    if approval.request_id != plan.request_id:
        raise SafetyViolation("approval request does not match action plan")
    if approval.plan_hash != plan.plan_hash:
        raise SafetyViolation("approval is stale because the action plan changed")


def require_fixture_marker(root: Path) -> Path:
    resolved = root.resolve()
    marker = resolved / MARKER
    if not marker.is_file():
        raise SafetyViolation("destructive execution requires a marked demo fixture root")
    if resolved == Path(resolved.anchor) or resolved == Path.cwd().resolve():
        raise SafetyViolation("refusing to execute against a broad filesystem target")
    return resolved


def require_namespace(plan: ActionPlan, prefix: str) -> None:
    invalid = sorted(
        decision.target_urn for decision in plan.decisions if prefix not in decision.target_urn
    )
    if invalid:
        raise SafetyViolation(
            "action plan contains targets outside the allocated DataHub namespace: "
            + ", ".join(invalid)
        )
