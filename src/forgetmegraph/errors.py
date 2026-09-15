"""Typed application errors with stable API semantics."""


class ForgetMeGraphError(Exception):
    """Base class for expected, privacy-safe application failures."""


class ConfigurationError(ForgetMeGraphError, ValueError):
    """Required runtime configuration is missing or invalid."""


class PolicyViolation(ForgetMeGraphError, ValueError):
    """A requested operation violates a fail-closed workflow policy."""


class StalePlanError(PolicyViolation):
    """The confirmed plan hash no longer matches the deterministic plan."""


class IntegrationFailure(ForgetMeGraphError, RuntimeError):
    """An external integration failed without exposing sensitive details."""
