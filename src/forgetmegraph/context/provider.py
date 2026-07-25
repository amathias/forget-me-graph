from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from forgetmegraph.domain.models import Artifact, LineageEdge


class ContextProvider(Protocol):
    def artifacts(self) -> list[Artifact]: ...

    def downstream_edges(self) -> list[LineageEdge]: ...


class FixtureContextProvider:
    """Local deterministic provider used before the live DataHub MCP connection is available."""

    def __init__(self, path: Path) -> None:
        self._payload = json.loads(path.read_text(encoding="utf-8"))

    def artifacts(self) -> list[Artifact]:
        return [Artifact.model_validate(item) for item in self._payload["artifacts"]]

    def downstream_edges(self) -> list[LineageEdge]:
        return [LineageEdge.model_validate(item) for item in self._payload["edges"]]
