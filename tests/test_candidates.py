import requests

from m2s3om_graph.candidates.blablador import (
    last_suggestion_error,
    suggest_candidate_mappings,
)


def test_candidate_suggestions_heuristic(monkeypatch) -> None:
    monkeypatch.delenv("BLABLADOR_API_KEY", raising=False)
    suggestions = suggest_candidate_mappings(
        "publicationYear",
        ["dcterms:issued", "dcterms:title", "dcterms:relation"],
        max_candidates=2,
    )
    assert len(suggestions) == 2
    assert suggestions[0].confidence <= 0.79
    assert suggestions[0].target_path.startswith("dcterms:")


def test_candidate_suggestions_records_llm_failure(monkeypatch) -> None:
    def _raise_request_error(*args: object, **kwargs: object) -> object:
        raise requests.Timeout("request timed out")

    monkeypatch.setenv("BLABLADOR_API_KEY", "demo")
    monkeypatch.setattr(
        "m2s3om_graph.candidates.blablador.requests.post", _raise_request_error
    )

    suggestions = suggest_candidate_mappings(
        "publicationYear",
        ["dcterms:issued", "dcterms:title", "dcterms:relation"],
        max_candidates=2,
    )

    diagnostics = last_suggestion_error()
    assert len(suggestions) == 2
    assert diagnostics is not None
    assert diagnostics["source"] == "candidate_suggestions"
    assert diagnostics["operation"] == "suggest_candidate_mappings.request"
    assert diagnostics["error_type"] == "Timeout"
