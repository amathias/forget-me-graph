import os

# Test modules build settings during import, so remove ambient application
# configuration before they import the module-level FastAPI application.
_APPLICATION_ENVIRONMENT_VARIABLES = (
    "PROJECT_SLUG",
    "APP_HOST",
    "APP_PORT",
    "APP_PUBLIC_URL",
    "APP_STATE_DIR",
    "DATAHUB_GMS_URL",
    "DATAHUB_MCP_URL",
    "DATAHUB_TOKEN",
    "DATAHUB_DOMAIN",
    "DATAHUB_PROJECT_TAG",
    "DATAHUB_URN_PREFIX",
    "DATAHUB_PROBE_URN",
    "DEMO_FIXTURE_ROOT",
    "FMG_SELECTOR_SECRET",
    "DEMO_ALLOWED_SELECTOR",
    "DEMO_PLAN_CLIENT_LIMIT_PER_MINUTE",
    "DEMO_PLAN_GLOBAL_LIMIT_PER_MINUTE",
    "DEMO_RUN_CLIENT_LIMIT_PER_TEN_MINUTES",
    "DEMO_RUN_GLOBAL_LIMIT_PER_TEN_MINUTES",
    "DEMO_RUN_COOLDOWN_SECONDS",
)
for name in _APPLICATION_ENVIRONMENT_VARIABLES:
    os.environ.pop(name, None)

os.environ["APP_ENV"] = "test"
