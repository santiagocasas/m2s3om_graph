from kaigraph.candidates import suggest_candidate_mappings


def test_candidate_suggestions_heuristic() -> None:
    suggestions = suggest_candidate_mappings(
        "publicationYear",
        ["dcterms:issued", "dcterms:title", "dcterms:relation"],
        max_candidates=2,
    )
    assert len(suggestions) == 2
    assert suggestions[0].confidence <= 0.79
    assert suggestions[0].target_path.startswith("dcterms:")
