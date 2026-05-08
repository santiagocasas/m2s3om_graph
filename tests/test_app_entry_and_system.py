from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

_APP_SPEC = spec_from_file_location(
    "m2s3om_graph_app_entry",
    Path(__file__).resolve().parents[1] / "app" / "app.py",
)
assert _APP_SPEC is not None and _APP_SPEC.loader is not None
app_entry = module_from_spec(_APP_SPEC)
_APP_SPEC.loader.exec_module(app_entry)

from views import system


class _FakeTab:
    def __enter__(self) -> "_FakeTab":
        return self

    def __exit__(self, _exc_type, _exc, _tb) -> bool:
        return False


def test_app_main_renders_expected_tabs(monkeypatch) -> None:
    calls: list[str] = []
    tab_labels: list[str] = []

    monkeypatch.setattr(app_entry.st, "set_page_config", lambda **_kwargs: None)
    monkeypatch.setattr(app_entry.st, "title", lambda _text: None)
    monkeypatch.setattr(app_entry.st, "caption", lambda _text: None)
    monkeypatch.setattr(
        app_entry.st,
        "tabs",
        lambda labels: tab_labels.extend(labels)
        or [_FakeTab(), _FakeTab(), _FakeTab()],
    )
    monkeypatch.setattr(
        app_entry.system, "render_sidebar", lambda: calls.append("sidebar")
    )
    monkeypatch.setattr(app_entry, "ensure_seeded", lambda: calls.append("seeded"))
    monkeypatch.setattr(
        app_entry.crosswalks, "render", lambda: calls.append("crosswalks")
    )
    monkeypatch.setattr(app_entry.pipeline, "render", lambda: calls.append("pipeline"))
    monkeypatch.setattr(
        app_entry.transform, "render", lambda: calls.append("transform")
    )

    app_entry.main()

    assert tab_labels == [
        "1) Crosswalk Browser",
        "2) Pipeline",
        "3) Convert One Record",
    ]
    assert calls == ["sidebar", "seeded", "crosswalks", "pipeline", "transform"]


def test_system_env_rows_reflects_key_presence(monkeypatch) -> None:
    monkeypatch.delenv("BLABLADOR_API_KEY", raising=False)
    rows = system._env_rows()
    assert rows["BLABLADOR_API_KEY"] == "missing"

    monkeypatch.setenv("BLABLADOR_API_KEY", "token")
    rows = system._env_rows()
    assert rows["BLABLADOR_API_KEY"] == "loaded"


def test_fetch_blablador_models_cached_success(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class _Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "data": [
                    {"id": "zeta"},
                    {"id": "alpha"},
                    {"id": "alpha"},
                    {"name": "invalid"},
                ]
            }

    def _fake_get(url: str, headers: dict[str, str], timeout: int) -> _Response:
        calls["url"] = url
        calls["headers"] = headers
        calls["timeout"] = timeout
        return _Response()

    system._fetch_blablador_models_cached.clear()
    monkeypatch.setattr(system.requests, "get", _fake_get)

    models, error = system._fetch_blablador_models_cached("https://example.org/v1", "k")
    assert error is None
    assert models == ["alpha", "zeta"]
    assert calls["url"] == "https://example.org/v1/models"


def test_fetch_blablador_models_cached_missing_key() -> None:
    system._fetch_blablador_models_cached.clear()
    models, error = system._fetch_blablador_models_cached("https://example.org/v1", " ")
    assert models == []
    assert error == "BLABLADOR_API_KEY is missing"
