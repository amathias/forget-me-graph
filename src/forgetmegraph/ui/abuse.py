from __future__ import annotations

import math
from collections import defaultdict, deque
from collections.abc import Callable
from threading import Lock
from time import monotonic


class DemoCapacityError(RuntimeError):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__("public demo capacity is temporarily limited")
        self.retry_after_seconds = max(1, retry_after_seconds)


class DemoAbuseGuard:
    """Process-local admission control for the unauthenticated public demo."""

    def __init__(self, *, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._lock = Lock()
        self._plan_by_client: dict[str, deque[float]] = defaultdict(deque)
        self._plan_global: deque[float] = deque()
        self._run_by_client: dict[str, deque[float]] = defaultdict(deque)
        self._run_global: deque[float] = deque()
        self._last_run_started_at: float | None = None
        self._run_active = False

    @staticmethod
    def _prune(samples: deque[float], *, now: float, window_seconds: int) -> None:
        cutoff = now - window_seconds
        while samples and samples[0] <= cutoff:
            samples.popleft()

    @staticmethod
    def _retry_after(samples: deque[float], *, now: float, window_seconds: int) -> int:
        if not samples:
            return 1
        return max(1, math.ceil(window_seconds - (now - samples[0])))

    def admit_plan(
        self,
        client_key: str,
        *,
        client_limit: int,
        global_limit: int,
        window_seconds: int = 60,
    ) -> None:
        now = self._clock()
        with self._lock:
            client_samples = self._plan_by_client[client_key]
            self._prune(client_samples, now=now, window_seconds=window_seconds)
            self._prune(self._plan_global, now=now, window_seconds=window_seconds)
            if len(client_samples) >= client_limit:
                raise DemoCapacityError(
                    self._retry_after(
                        client_samples,
                        now=now,
                        window_seconds=window_seconds,
                    )
                )
            if len(self._plan_global) >= global_limit:
                raise DemoCapacityError(
                    self._retry_after(
                        self._plan_global,
                        now=now,
                        window_seconds=window_seconds,
                    )
                )
            client_samples.append(now)
            self._plan_global.append(now)

    def begin_run(
        self,
        client_key: str,
        *,
        client_limit: int,
        global_limit: int,
        cooldown_seconds: int,
        window_seconds: int = 600,
    ) -> None:
        now = self._clock()
        with self._lock:
            if self._run_active:
                raise DemoCapacityError(5)
            if self._last_run_started_at is not None:
                remaining = cooldown_seconds - (now - self._last_run_started_at)
                if remaining > 0:
                    raise DemoCapacityError(math.ceil(remaining))

            client_samples = self._run_by_client[client_key]
            self._prune(client_samples, now=now, window_seconds=window_seconds)
            self._prune(self._run_global, now=now, window_seconds=window_seconds)
            if len(client_samples) >= client_limit:
                raise DemoCapacityError(
                    self._retry_after(
                        client_samples,
                        now=now,
                        window_seconds=window_seconds,
                    )
                )
            if len(self._run_global) >= global_limit:
                raise DemoCapacityError(
                    self._retry_after(
                        self._run_global,
                        now=now,
                        window_seconds=window_seconds,
                    )
                )

            client_samples.append(now)
            self._run_global.append(now)
            self._last_run_started_at = now
            self._run_active = True

    def begin_unrestricted_run(self) -> None:
        """Serialize local/test runs without recording public rate history."""
        with self._lock:
            if self._run_active:
                raise DemoCapacityError(1)
            self._run_active = True

    def finish_run(self) -> None:
        with self._lock:
            self._run_active = False

    def reset(self) -> None:
        """Clear process-local state for deterministic tests."""
        with self._lock:
            self._plan_by_client.clear()
            self._plan_global.clear()
            self._run_by_client.clear()
            self._run_global.clear()
            self._last_run_started_at = None
            self._run_active = False
