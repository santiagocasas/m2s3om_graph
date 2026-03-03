import time
from dataclasses import dataclass
from typing import Callable


@dataclass
class SurrealProbeResult:
    ready: bool
    error: str | None = None


def probe_surreal_ready(
    *,
    url: str,
    username: str,
    password: str,
    namespace: str,
    database: str,
) -> SurrealProbeResult:
    try:
        from surrealdb import Surreal

        client = Surreal(url)
        if url != "mem://":
            _ = client.signin({"username": username, "password": password})
        client.use(namespace, database)
        _ = client.query("RETURN 1;")
        return SurrealProbeResult(ready=True)
    except Exception as exc:
        return SurrealProbeResult(ready=False, error=str(exc))


def wait_for_surreal_ready(
    *,
    url: str,
    username: str,
    password: str,
    namespace: str,
    database: str,
    attempts: int = 45,
    delay_seconds: float = 1.0,
    probe_fn: Callable[[], SurrealProbeResult] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> SurrealProbeResult:
    if attempts < 1:
        attempts = 1
    if delay_seconds < 0:
        delay_seconds = 0

    def default_probe() -> SurrealProbeResult:
        return probe_surreal_ready(
            url=url,
            username=username,
            password=password,
            namespace=namespace,
            database=database,
        )

    probe = probe_fn or default_probe
    last_error = "unknown_error"

    for index in range(attempts):
        result = probe()
        if result.ready:
            return result
        if result.error:
            last_error = result.error
        if index < attempts - 1:
            sleep_fn(delay_seconds)

    return SurrealProbeResult(ready=False, error=last_error)
