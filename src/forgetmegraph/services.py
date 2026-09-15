from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from forgetmegraph.config import Settings
from forgetmegraph.context.datahub import DataHubCapabilityStatus, probe_datahub
from forgetmegraph.demo.workflow import prepare_demo_workflow, run_workflow


@dataclass(frozen=True)
class ApplicationServices:
    """Explicit application dependencies captured once by the app factory."""

    datahub_probe: Callable[[Settings], Awaitable[DataHubCapabilityStatus]]
    prepare_workflow: Callable[..., Any]
    run_workflow: Callable[..., Any]


def default_application_services() -> ApplicationServices:
    return ApplicationServices(
        datahub_probe=probe_datahub,
        prepare_workflow=prepare_demo_workflow,
        run_workflow=run_workflow,
    )
