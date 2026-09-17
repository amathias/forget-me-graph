from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

_DATASET_PREFIX = "urn:li:dataset:("
_PLATFORM_PREFIX = "urn:li:dataPlatform:"


@dataclass(frozen=True)
class DatasetUrn:
    entity_type: Literal["dataset"]
    platform: str
    name: str
    environment: str

    @property
    def platform_urn(self) -> str:
        return f"{_PLATFORM_PREFIX}{self.platform}"


def parse_dataset_urn(urn: str) -> DatasetUrn:
    """Parse the exact three-part dataset URN form used by this project."""
    if not urn.startswith(_DATASET_PREFIX) or not urn.endswith(")"):
        raise ValueError("unsupported or malformed DataHub dataset URN")
    body = urn[len(_DATASET_PREFIX) : -1]
    components = body.split(",")
    if len(components) != 3:
        raise ValueError("unsupported or malformed DataHub dataset URN")
    platform_urn, name, environment = components
    platform = platform_urn.removeprefix(_PLATFORM_PREFIX)
    if (
        not platform_urn.startswith(_PLATFORM_PREFIX)
        or not platform
        or ":" in platform
        or not name
        or not environment
        or any(
            not character.isprintable() or character.isspace() or character in "()"
            for value in components
            for character in value
        )
    ):
        raise ValueError("unsupported or malformed DataHub dataset URN")
    return DatasetUrn(
        entity_type="dataset",
        platform=platform,
        name=name,
        environment=environment,
    )


def dataset_urn_is_namespaced(urn: str, namespace_prefix: str) -> bool:
    if not namespace_prefix:
        return False
    name = parse_dataset_urn(urn).name
    return name.startswith(namespace_prefix) and len(name) > len(namespace_prefix)
