from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _positive_int_env(name: str, default: int) -> int:
    value = int(os.getenv(name, str(default)))
    if value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


@dataclass(frozen=True)
class Settings:
    project_slug: str
    app_env: str
    app_host: str
    app_port: int
    app_public_url: str | None
    app_state_dir: Path
    datahub_gms_url: str | None
    datahub_mcp_url: str | None
    datahub_token: str | None
    datahub_domain: str
    datahub_project_tag: str
    datahub_urn_prefix: str
    datahub_probe_urn: str
    demo_fixture_root: Path
    selector_secret: str | None
    demo_allowed_selector: str
    demo_plan_client_limit_per_minute: int
    demo_plan_global_limit_per_minute: int
    demo_run_client_limit_per_ten_minutes: int
    demo_run_global_limit_per_ten_minutes: int
    demo_run_cooldown_seconds: int

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            project_slug=os.getenv("PROJECT_SLUG", "forget-me-graph"),
            app_env=os.getenv("APP_ENV", "local"),
            app_host=os.getenv("APP_HOST", "127.0.0.1"),
            app_port=int(os.getenv("APP_PORT", "8103")),
            app_public_url=os.getenv("APP_PUBLIC_URL") or None,
            app_state_dir=Path(os.getenv("APP_STATE_DIR", "demo/state/forget-me-graph")),
            datahub_gms_url=os.getenv("DATAHUB_GMS_URL") or None,
            datahub_mcp_url=os.getenv("DATAHUB_MCP_URL") or None,
            datahub_token=os.getenv("DATAHUB_TOKEN") or None,
            datahub_domain=os.getenv("DATAHUB_DOMAIN", "Demo / Forget-Me-Graph"),
            datahub_project_tag=os.getenv("DATAHUB_PROJECT_TAG", "project-forget-me-graph"),
            datahub_urn_prefix=os.getenv("DATAHUB_URN_PREFIX", "forgetme."),
            datahub_probe_urn=os.getenv(
                "DATAHUB_PROBE_URN",
                "urn:li:dataset:(urn:li:dataPlatform:duckdb,forgetme.raw.customers,PROD)",
            ),
            demo_fixture_root=Path(os.getenv("DEMO_FIXTURE_ROOT", "demo/fixtures/forget-me-graph")),
            selector_secret=os.getenv("FMG_SELECTOR_SECRET") or None,
            demo_allowed_selector=os.getenv("DEMO_ALLOWED_SELECTOR", "42"),
            demo_plan_client_limit_per_minute=_positive_int_env(
                "DEMO_PLAN_CLIENT_LIMIT_PER_MINUTE",
                20,
            ),
            demo_plan_global_limit_per_minute=_positive_int_env(
                "DEMO_PLAN_GLOBAL_LIMIT_PER_MINUTE",
                120,
            ),
            demo_run_client_limit_per_ten_minutes=_positive_int_env(
                "DEMO_RUN_CLIENT_LIMIT_PER_TEN_MINUTES",
                3,
            ),
            demo_run_global_limit_per_ten_minutes=_positive_int_env(
                "DEMO_RUN_GLOBAL_LIMIT_PER_TEN_MINUTES",
                12,
            ),
            demo_run_cooldown_seconds=_positive_int_env(
                "DEMO_RUN_COOLDOWN_SECONDS",
                15,
            ),
        )
