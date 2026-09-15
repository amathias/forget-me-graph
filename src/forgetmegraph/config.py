from __future__ import annotations

import os
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from urllib.parse import urlparse

from forgetmegraph.errors import ConfigurationError
from forgetmegraph.privacy.selector import SelectorProtectionError, validate_selector_secret


class AppEnvironment(StrEnum):
    LOCAL = "local"
    TEST = "test"
    HACKATHON = "hackathon"
    PRODUCTION = "production"


def _app_environment() -> AppEnvironment:
    raw_value = os.getenv("APP_ENV")
    if raw_value is None or not raw_value.strip():
        raise ConfigurationError(
            "APP_ENV is required and must be one of: local, test, hackathon, production"
        )
    try:
        return AppEnvironment(raw_value.strip().lower())
    except ValueError as exc:
        raise ConfigurationError(
            "APP_ENV must be one of: local, test, hackathon, production"
        ) from exc


def _positive_int_env(name: str, default: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be a positive integer") from exc
    if value < 1:
        raise ConfigurationError(f"{name} must be a positive integer")
    return value


def _port_env(name: str, default: int) -> int:
    value = _positive_int_env(name, default)
    if value > 65535:
        raise ConfigurationError(f"{name} must be between 1 and 65535")
    return value


def _valid_http_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


@dataclass(frozen=True)
class Settings:
    project_slug: str
    app_env: AppEnvironment
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

    def __post_init__(self) -> None:
        if not isinstance(self.app_env, AppEnvironment):
            raise ConfigurationError("app_env must be a supported AppEnvironment")
        if not 1 <= self.app_port <= 65535:
            raise ConfigurationError("APP_PORT must be between 1 and 65535")
        positive_values = {
            "DEMO_PLAN_CLIENT_LIMIT_PER_MINUTE": self.demo_plan_client_limit_per_minute,
            "DEMO_PLAN_GLOBAL_LIMIT_PER_MINUTE": self.demo_plan_global_limit_per_minute,
            "DEMO_RUN_CLIENT_LIMIT_PER_TEN_MINUTES": self.demo_run_client_limit_per_ten_minutes,
            "DEMO_RUN_GLOBAL_LIMIT_PER_TEN_MINUTES": self.demo_run_global_limit_per_ten_minutes,
            "DEMO_RUN_COOLDOWN_SECONDS": self.demo_run_cooldown_seconds,
        }
        for name, value in positive_values.items():
            if value < 1:
                raise ConfigurationError(f"{name} must be a positive integer")
        if self.selector_secret is not None:
            try:
                validate_selector_secret(self.selector_secret)
            except SelectorProtectionError as exc:
                raise ConfigurationError("FMG_SELECTOR_SECRET is invalid") from exc
        for name, value in (
            ("APP_PUBLIC_URL", self.app_public_url),
            ("DATAHUB_GMS_URL", self.datahub_gms_url),
            ("DATAHUB_MCP_URL", self.datahub_mcp_url),
        ):
            if value is not None and not _valid_http_url(value):
                raise ConfigurationError(f"{name} must be an absolute HTTP(S) URL")
        if self.app_env in {AppEnvironment.HACKATHON, AppEnvironment.PRODUCTION}:
            required_values = (
                self.selector_secret,
                self.datahub_gms_url,
                self.datahub_mcp_url,
                self.datahub_token,
            )
            if not all(value and value.strip() for value in required_values):
                raise ConfigurationError(
                    "non-local runtime configuration requires selector protection "
                    "and DataHub access"
                )

    @classmethod
    def from_env(cls) -> Settings:
        return cls(
            project_slug=os.getenv("PROJECT_SLUG", "forget-me-graph"),
            app_env=_app_environment(),
            app_host=os.getenv("APP_HOST", "127.0.0.1"),
            app_port=_port_env("APP_PORT", 8103),
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
