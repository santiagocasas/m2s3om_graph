import requests

from kaigraph.rdamsc.llm_extract import extract_mapping_candidates_with_meta


class _FakeResponse:
    def __init__(self, payload: dict[str, object], status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")

    def json(self) -> dict[str, object]:
        return self._payload


def test_extract_with_meta_missing_api_key_uses_heuristic(monkeypatch) -> None:
    monkeypatch.delenv("BLABLADOR_API_KEY", raising=False)
    candidates, meta = extract_mapping_candidates_with_meta(
        "title -> dcterms:title",
        "A",
        "B",
    )

    assert meta["backend"] == "heuristic"
    assert meta["llm_error"] == "missing_api_key"
    assert len(candidates) == 1
    assert candidates[0]["source_path"] == "title"


def test_extract_with_meta_retries_then_succeeds(monkeypatch) -> None:
    monkeypatch.setenv("BLABLADOR_API_KEY", "test-key")
    monkeypatch.setenv("KAIGRAPH_LLM_RETRIES", "2")
    monkeypatch.setenv("KAIGRAPH_LLM_TIMEOUT_S", "15")
    calls = {"count": 0}

    def _fake_post(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise requests.Timeout("timed out")
        return _FakeResponse(
            {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '[{"source_path":"title","target_path":"dcterms:title",'
                                '"mapping_type":"direct","confidence":0.9}]'
                            )
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("kaigraph.rdamsc.llm_extract.requests.post", _fake_post)
    monkeypatch.setattr("kaigraph.rdamsc.llm_extract.time.sleep", lambda *_args: None)

    candidates, meta = extract_mapping_candidates_with_meta("x", "A", "B")
    assert meta["backend"] == "llm_json"
    assert meta["attempts_json"] == 3
    assert len(candidates) == 1


def test_extract_with_meta_relaxed_fallback(monkeypatch) -> None:
    monkeypatch.setenv("BLABLADOR_API_KEY", "test-key")
    calls = {"count": 0}

    def _fake_post(*_args, **_kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return _FakeResponse(
                {"choices": [{"message": {"content": "not json output"}}]}
            )
        return _FakeResponse(
            {"choices": [{"message": {"content": "fieldA\tfieldB\tevidence line"}}]}
        )

    monkeypatch.setattr("kaigraph.rdamsc.llm_extract.requests.post", _fake_post)

    candidates, meta = extract_mapping_candidates_with_meta("x", "A", "B")
    assert meta["backend"] == "llm_relaxed"
    assert meta["attempts_json"] == 1
    assert meta["attempts_relaxed"] == 1
    assert len(candidates) == 1
    assert candidates[0]["source_path"] == "fieldA"
