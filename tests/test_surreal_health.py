from m2s3om_graph.db.surreal_health import SurrealProbeResult, wait_for_surreal_ready


def test_wait_for_surreal_ready_retries_until_success() -> None:
    calls = {"count": 0}

    def probe() -> SurrealProbeResult:
        calls["count"] += 1
        if calls["count"] < 3:
            return SurrealProbeResult(ready=False, error="connection refused")
        return SurrealProbeResult(ready=True)

    sleeps: list[float] = []

    def sleep_fn(value: float) -> None:
        sleeps.append(value)

    result = wait_for_surreal_ready(
        url="ws://localhost:8000/rpc",
        username="root",
        password="root",
        namespace="m2s3om_graph",
        database="crosswalk",
        attempts=5,
        delay_seconds=0.25,
        probe_fn=probe,
        sleep_fn=sleep_fn,
    )

    assert result.ready is True
    assert calls["count"] == 3
    assert sleeps == [0.25, 0.25]


def test_wait_for_surreal_ready_reports_last_error_on_failure() -> None:
    calls = {"count": 0}

    def probe() -> SurrealProbeResult:
        calls["count"] += 1
        return SurrealProbeResult(ready=False, error=f"refused-{calls['count']}")

    result = wait_for_surreal_ready(
        url="ws://localhost:8000/rpc",
        username="root",
        password="root",
        namespace="m2s3om_graph",
        database="crosswalk",
        attempts=3,
        delay_seconds=0,
        probe_fn=probe,
        sleep_fn=lambda _: None,
    )

    assert result.ready is False
    assert result.error == "refused-3"
