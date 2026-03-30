from kaigraph.db import MappingType
from kaigraph.ingest.deterministic.types import (
    DeterministicCandidate,
    DeterministicDiagnostics,
)


def test_deterministic_candidate_to_record_uses_mapping_value() -> None:
    candidate = DeterministicCandidate(
        source_path="title",
        target_path="dcterms:title",
        mapping_type=MappingType.DIRECT,
        confidence=0.9,
        notes="n",
        evidence="e",
        extractor_name="markdown",
    )
    assert candidate.to_record() == {
        "source_path": "title",
        "target_path": "dcterms:title",
        "mapping_type": "direct",
        "confidence": 0.9,
        "notes": "n",
        "evidence": "e",
    }


def test_deterministic_diagnostics_to_record_copies_counter_map() -> None:
    diagnostics = DeterministicDiagnostics(
        total_chars=10,
        normalized_chars=8,
        total_lines=2,
        extractor_counts={"markdown": 3},
        candidates_before_dedupe=5,
        candidates_after_dedupe=4,
    )

    record = diagnostics.to_record()
    assert record["extractor_counts"] == {"markdown": 3}

    extractor_counts = record["extractor_counts"]
    assert isinstance(extractor_counts, dict)
    extractor_counts["markdown"] = 99
    assert diagnostics.extractor_counts["markdown"] == 3
