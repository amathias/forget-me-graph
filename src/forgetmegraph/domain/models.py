from __future__ import annotations

import json
from enum import StrEnum
from hashlib import sha256
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ArtifactType(StrEnum):
    RAW_DATASET = "raw_dataset"
    DERIVED_DATASET = "derived_dataset"
    FEATURE_TABLE = "feature_table"
    VECTOR_INDEX = "vector_index"
    CACHE = "cache"
    EXPORT = "export"
    TRAINING_SNAPSHOT = "training_snapshot"
    ML_MODEL = "ml_model"
    AGGREGATE = "aggregate"
    UNKNOWN = "unknown"


class ActionType(StrEnum):
    ROW_PURGE = "row_purge"
    REBUILD = "rebuild"
    VECTOR_DELETE_REINDEX = "vector_delete_reindex"
    CACHE_EVICT = "cache_evict"
    EXPORT_REPLACE = "export_replace"
    RETRAIN = "retrain"
    VERIFY_ONLY = "verify_only"
    EXEMPT = "exempt"
    ESCALATE = "escalate"


class DecisionStatus(StrEnum):
    READY = "ready"
    BLOCKED = "blocked"
    EXEMPT = "exempt"
    OUT_OF_SCOPE = "out_of_scope"


class SelectorOperator(StrEnum):
    EQUALS = "equals"


class SubjectSelector(BaseModel):
    """Intake-only selector. This model must never be logged or serialized as evidence."""

    model_config = ConfigDict(extra="forbid")

    subject_type: str = Field(min_length=1, max_length=100)
    field: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    operator: SelectorOperator = SelectorOperator.EQUALS
    value: str = Field(min_length=1, max_length=512, repr=False)


class ProtectedSelector(BaseModel):
    """Safe-to-persist selector representation."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    subject_type: str
    field: str
    operator: SelectorOperator
    token: str
    ciphertext: str = Field(repr=False, exclude=True)


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    urn: str
    name: str
    artifact_type: ArtifactType
    adapter: str
    policy: str = "required"
    owner: str = "demo-platform-team"


class LineageEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_urn: str
    destination_urn: str


class SelectorMapping(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_urn: str
    source_field: str
    destination_urn: str
    destination_field: str
    mapping_type: str
    verification_strategy: str
    owner: str
    evidence: str
    version: int = 1


class ArtifactDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    target_urn: str
    artifact_type: ArtifactType
    action: ActionType
    status: DecisionStatus
    selector_field: str | None
    selector_token: str
    lineage_path: list[str]
    reason: str
    prerequisites: list[str] = Field(default_factory=list)
    mapping_version: int | None = None


class ActionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str
    selector_token: str
    entrypoint_urns: list[str]
    decisions: list[ArtifactDecision]
    plan_hash: str

    @classmethod
    def create(
        cls,
        *,
        request_id: str,
        selector_token: str,
        entrypoint_urns: list[str],
        decisions: list[ArtifactDecision],
    ) -> ActionPlan:
        canonical: dict[str, Any] = {
            "request_id": request_id,
            "selector_token": selector_token,
            "entrypoint_urns": sorted(entrypoint_urns),
            "decisions": [
                decision.model_dump(mode="json")
                for decision in sorted(decisions, key=lambda item: item.target_urn)
            ],
        }
        digest = sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        return cls(**canonical, plan_hash=digest)
