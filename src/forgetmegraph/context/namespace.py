from __future__ import annotations

from dataclasses import dataclass

_DATASET_PREFIX = "urn:li:dataset:("
_PLATFORM_PREFIX = "urn:li:dataPlatform:"


@dataclass(frozen=True)
class DatasetUrn:
    platform_urn: str
    name: str
    environment: str


def parse_dataset_urn(urn: str) -> DatasetUrn:
    """Parse the exact three-part dataset URN form used by this project."""
    if not urn.startswith(_DATASET_PREFIX) or not urn.endswith(")"):
        raise ValueError("unsupported or malformed DataHub dataset URN")
    body = urn[len(_DATASET_PREFIX) : -1]
    platform_urn, first_separator, remainder = body.partition(",")
    name, last_separator, environment = remainder.rpartition(",")
    if (
        not first_separator
        or not last_separator
        or not platform_urn.startswith(_PLATFORM_PREFIX)
        or platform_urn == _PLATFORM_PREFIX
        or not name
        or not environment
    ):
        raise ValueError("unsupported or malformed DataHub dataset URN")
    return DatasetUrn(
        platform_urn=platform_urn,
        name=name,
        environment=environment,
    )


def dataset_urn_is_namespaced(urn: str, namespace_prefix: str) -> bool:
    if not namespace_prefix:
        return False
    name = parse_dataset_urn(urn).name
    return name.startswith(namespace_prefix) and len(name) > len(namespace_prefix)
