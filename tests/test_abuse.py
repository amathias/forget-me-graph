import pytest

from forgetmegraph.ui.abuse import DemoAbuseGuard, DemoCapacityError


class FakeClock:
    def __init__(self) -> None:
        self.now = 1_000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_plan_limits_are_per_client_and_global() -> None:
    clock = FakeClock()
    guard = DemoAbuseGuard(clock=clock)

    guard.admit_plan("judge-a", client_limit=2, global_limit=3)
    guard.admit_plan("judge-a", client_limit=2, global_limit=3)
    with pytest.raises(DemoCapacityError, match="capacity") as client_error:
        guard.admit_plan("judge-a", client_limit=2, global_limit=3)
    assert client_error.value.retry_after_seconds == 60

    guard.admit_plan("judge-b", client_limit=2, global_limit=3)
    with pytest.raises(DemoCapacityError) as global_error:
        guard.admit_plan("judge-c", client_limit=2, global_limit=3)
    assert global_error.value.retry_after_seconds == 60

    clock.advance(60)
    guard.admit_plan("judge-a", client_limit=2, global_limit=3)


def test_run_admission_rejects_concurrency_cooldown_and_repeated_client() -> None:
    clock = FakeClock()
    guard = DemoAbuseGuard(clock=clock)

    guard.begin_run("judge-a", client_limit=2, global_limit=4, cooldown_seconds=15)
    with pytest.raises(DemoCapacityError) as busy:
        guard.begin_run("judge-b", client_limit=2, global_limit=4, cooldown_seconds=15)
    assert busy.value.retry_after_seconds == 5

    guard.finish_run()
    with pytest.raises(DemoCapacityError) as cooldown:
        guard.begin_run("judge-b", client_limit=2, global_limit=4, cooldown_seconds=15)
    assert cooldown.value.retry_after_seconds == 15

    clock.advance(15)
    guard.begin_run("judge-a", client_limit=2, global_limit=4, cooldown_seconds=15)
    guard.finish_run()
    clock.advance(15)
    with pytest.raises(DemoCapacityError) as repeated:
        guard.begin_run("judge-a", client_limit=2, global_limit=4, cooldown_seconds=15)
    assert repeated.value.retry_after_seconds == 570

    guard.begin_run("judge-b", client_limit=2, global_limit=4, cooldown_seconds=15)
    guard.finish_run()
