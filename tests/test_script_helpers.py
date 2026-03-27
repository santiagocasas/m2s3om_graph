import importlib
import importlib.util
from pathlib import Path
import sys

from kaigraph.db.surreal_health import SurrealProbeResult
from kaigraph.rdamsc.pipeline_stats_cli import main as pipeline_stats_main

HELPERS_DIR = Path(__file__).resolve().parents[1] / "scripts" / "helpers"
sys.path.insert(0, str(HELPERS_DIR))

is_port_open = importlib.import_module("is_port_open")
wait_surreal_ready = importlib.import_module("wait_surreal_ready")


def _load_helper_module(module_name: str, filename: str):
    helper_path = Path(__file__).resolve().parents[1] / "scripts" / "helpers" / filename
    spec = importlib.util.spec_from_file_location(module_name, helper_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rdamsc_pipeline_stats = _load_helper_module(
    "rdamsc_pipeline_stats_wrapper", "../rdamsc_pipeline_stats.py"
)


class _FakeSocket:
    def __init__(self, return_code: int) -> None:
        self.return_code = return_code
        self.endpoint: tuple[str, int] | None = None
        self.timeout: float | None = None

    def __enter__(self) -> "_FakeSocket":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> bool:
        return False

    def settimeout(self, timeout: float) -> None:
        self.timeout = timeout

    def connect_ex(self, endpoint: tuple[str, int]) -> int:
        self.endpoint = endpoint
        return self.return_code


def test_is_port_open_usage_error(monkeypatch) -> None:
    monkeypatch.setattr(is_port_open.sys, "argv", ["is_port_open.py"])
    assert is_port_open.main() == 2


def test_is_port_open_success_and_failure(monkeypatch) -> None:
    open_socket = _FakeSocket(return_code=0)
    monkeypatch.setattr(
        is_port_open.socket,
        "socket",
        lambda *_args, **_kwargs: open_socket,
    )
    monkeypatch.setattr(
        is_port_open.sys, "argv", ["is_port_open.py", "localhost", "1234"]
    )
    assert is_port_open.main() == 0
    assert open_socket.endpoint == ("localhost", 1234)
    assert open_socket.timeout == 1.0

    closed_socket = _FakeSocket(return_code=111)
    monkeypatch.setattr(
        is_port_open.socket,
        "socket",
        lambda *_args, **_kwargs: closed_socket,
    )
    monkeypatch.setattr(
        is_port_open.sys, "argv", ["is_port_open.py", "localhost", "4321"]
    )
    assert is_port_open.main() == 1


def test_wait_surreal_ready_main_success(monkeypatch, capsys) -> None:
    calls: dict[str, object] = {}

    def _fake_wait_for_surreal_ready(**kwargs):
        calls.update(kwargs)
        return SurrealProbeResult(ready=True)

    monkeypatch.setattr(
        wait_surreal_ready, "wait_for_surreal_ready", _fake_wait_for_surreal_ready
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "wait_surreal_ready.py",
            "--url",
            "ws://localhost:8000/rpc",
            "--user",
            "root",
            "--password",
            "secret",
            "--namespace",
            "kaigraph",
            "--database",
            "crosswalk",
            "--attempts",
            "3",
            "--delay",
            "0.1",
        ],
    )

    assert wait_surreal_ready.main() == 0
    captured = capsys.readouterr()
    assert "SurrealDB is ready" in captured.out
    assert calls["attempts"] == 3
    assert calls["delay_seconds"] == 0.1


def test_wait_surreal_ready_main_failure(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        wait_surreal_ready,
        "wait_for_surreal_ready",
        lambda **_kwargs: SurrealProbeResult(ready=False, error="timeout"),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "wait_surreal_ready.py",
            "--url",
            "ws://localhost:8000/rpc",
            "--user",
            "root",
            "--password",
            "secret",
            "--namespace",
            "kaigraph",
            "--database",
            "crosswalk",
        ],
    )

    assert wait_surreal_ready.main() == 1
    captured = capsys.readouterr()
    assert "SurrealDB readiness check failed: timeout" in captured.out


def test_rdamsc_pipeline_stats_wrapper_delegates_to_cli_main() -> None:
    assert rdamsc_pipeline_stats.main is pipeline_stats_main
