from pathlib import Path
import sys

import requests

sys.path.insert(
    0,
    str(
        Path(__file__).resolve().parents[1]
        / "claude_suggestions"
        / "m2s3om-suggest-api"
        / "m2s3om-suggest-api"
    ),
)

import main
from fastapi.testclient import TestClient


def test_health_ok() -> None:
    client = TestClient(main.app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_suggest_happy_path_with_mocked_llm(monkeypatch) -> None:
    monkeypatch.setenv("BLABLADOR_API_KEY", "test-key")

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '[{"source_path": "a", "target_path": "b", '
                                '"mapping_type": "direct", "confidence": 0.9, '
                                '"evidence": "e"}]'
                            )
                        }
                    }
                ]
            }

    def fake_post(*args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(main.requests, "post", fake_post)

    client = TestClient(main.app)
    response = client.post(
        "/suggest",
        json={
            "source_standard": "src",
            "target_standard": "dst",
            "source_field": "field",
            "target_schema_fields": ["a", "b"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert len(body) == 1
    assert body[0]["source_path"] == "a"
    assert body[0]["mapping_type"] == "direct"


def test_suggest_returns_500_when_api_key_missing(monkeypatch) -> None:
    monkeypatch.delenv("BLABLADOR_API_KEY", raising=False)

    client = TestClient(main.app)
    response = client.post(
        "/suggest",
        json={
            "source_standard": "src",
            "target_standard": "dst",
            "source_field": "field",
            "target_schema_fields": ["a"],
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "BLABLADOR_API_KEY not configured on this Space"


def test_suggest_returns_502_on_non_json_llm_response(monkeypatch) -> None:
    monkeypatch.setenv("BLABLADOR_API_KEY", "test-key")

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {
                "choices": [
                    {"message": {"content": "not json at all"}},
                ]
            }

    monkeypatch.setattr(main.requests, "post", lambda *args, **kwargs: FakeResponse())

    client = TestClient(main.app)
    response = client.post(
        "/suggest",
        json={
            "source_standard": "src",
            "target_standard": "dst",
            "source_field": "field",
            "target_schema_fields": ["a"],
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"].startswith(
        "Could not parse model output as JSON:"
    )


def test_suggest_returns_502_on_upstream_network_error(monkeypatch) -> None:
    monkeypatch.setenv("BLABLADOR_API_KEY", "test-key")

    def raise_connection_error(*args, **kwargs):
        raise requests.ConnectionError("boom")

    monkeypatch.setattr(main.requests, "post", raise_connection_error)

    client = TestClient(main.app)
    response = client.post(
        "/suggest",
        json={
            "source_standard": "src",
            "target_standard": "dst",
            "source_field": "field",
            "target_schema_fields": ["a"],
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"].startswith("Blablador request failed:")


def test_defaults_come_from_load_llm_runtime_config(monkeypatch) -> None:
    monkeypatch.delenv("BLABLADOR_API_KEY", raising=False)
    monkeypatch.delenv("BLABLADOR_BASE_URL", raising=False)
    monkeypatch.delenv("BLABLADOR_MODEL", raising=False)
    monkeypatch.delenv("M2S3OM_LLM_MODEL", raising=False)
    monkeypatch.delenv("M2S3OM_LLM_TIMEOUT_S", raising=False)
    monkeypatch.delenv("M2S3OM_LLM_RETRIES", raising=False)
    monkeypatch.delenv("M2S3OM_LLM_MAX_INPUT_CHARS", raising=False)

    config = main.load_llm_runtime_config()

    assert config.base_url == "https://api.helmholtz-blablador.fz-juelich.de/v1"
    assert config.model == "alias-fast"
