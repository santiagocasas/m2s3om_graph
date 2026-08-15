from pathlib import Path
import sys

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
