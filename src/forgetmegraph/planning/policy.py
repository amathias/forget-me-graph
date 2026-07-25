from forgetmegraph.domain.models import (
    ActionType,
    Artifact,
    ArtifactType,
    DecisionStatus,
)


def select_action(artifact: Artifact) -> tuple[ActionType, DecisionStatus, str]:
    if artifact.policy == "out_of_scope":
        return (
            ActionType.VERIFY_ONLY,
            DecisionStatus.OUT_OF_SCOPE,
            "Artifact is explicitly outside the approved demo scope.",
        )
    if artifact.policy == "exempt":
        return (
            ActionType.EXEMPT,
            DecisionStatus.EXEMPT,
            "Artifact has a documented aggregate-only exemption.",
        )

    action_by_type = {
        ArtifactType.RAW_DATASET: ActionType.ROW_PURGE,
        ArtifactType.DERIVED_DATASET: ActionType.REBUILD,
        ArtifactType.FEATURE_TABLE: ActionType.REBUILD,
        ArtifactType.VECTOR_INDEX: ActionType.VECTOR_DELETE_REINDEX,
        ArtifactType.CACHE: ActionType.CACHE_EVICT,
        ArtifactType.EXPORT: ActionType.EXPORT_REPLACE,
        ArtifactType.TRAINING_SNAPSHOT: ActionType.REBUILD,
        ArtifactType.ML_MODEL: ActionType.RETRAIN,
        ArtifactType.AGGREGATE: ActionType.REBUILD,
    }
    action = action_by_type.get(artifact.artifact_type, ActionType.ESCALATE)
    if action is ActionType.ESCALATE:
        return action, DecisionStatus.BLOCKED, "No deterministic policy exists for this artifact."
    return (
        action,
        DecisionStatus.READY,
        f"Policy selected {action.value} for {artifact.artifact_type}.",
    )
