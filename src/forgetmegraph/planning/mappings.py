from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from forgetmegraph.domain.models import SelectorMapping


class MappingRegistry:
    def __init__(self, mappings: Iterable[SelectorMapping]) -> None:
        self._mappings = {
            (item.source_urn, item.source_field, item.destination_urn): item for item in mappings
        }

    @classmethod
    def from_json(cls, path: Path) -> MappingRegistry:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return cls(SelectorMapping.model_validate(item) for item in payload["mappings"])

    def get(
        self, source_urn: str, source_field: str, destination_urn: str
    ) -> SelectorMapping | None:
        return self._mappings.get((source_urn, source_field, destination_urn))
