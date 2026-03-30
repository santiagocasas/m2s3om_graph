from kaigraph.db import MappingType
from kaigraph.ingest.deterministic.extractors import (
    extract_assignment_candidates,
    extract_markdown_table_candidates,
)
from kaigraph.ingest.deterministic.normalizers import normalize_text_for_deterministic


def test_normalize_text_for_deterministic_cleans_rtf_controls() -> None:
    text = (
        "{\\lang1033 titleproper}\\par\r\n"
        "{\\b unitdate} = E52 Time\u2014Span\\par\r"
        "value \u2013 field \u2192 dcterms:title"
    )
    normalized = normalize_text_for_deterministic(text)

    assert "\\lang1033" not in normalized
    assert "\\b" not in normalized
    assert "titleproper" in normalized
    assert "Time-Span" in normalized
    assert "value - field -> dcterms:title" in normalized


def test_extract_assignment_candidates_detects_mapping_types() -> None:
    text = "\n".join(
        [
            "titleproper = E35 Title",
            "identifier@scheme = dcterms:identifier",
            "name = Not present: Dublin Core",
            "aggregate = E22 is composed of title and subtitle",
            "joined = dcterms:title (join)",
            "bad source path = dcterms:ignored",
        ]
    )
    candidates = extract_assignment_candidates(text)

    by_source = {candidate.source_path: candidate for candidate in candidates}
    assert by_source["titleproper"].mapping_type == MappingType.DIRECT
    assert by_source["identifier@scheme"].mapping_type == MappingType.CONDITIONAL
    assert by_source["name"].mapping_type == MappingType.MISSING
    assert by_source["aggregate"].mapping_type == MappingType.AGGREGATION
    assert by_source["joined"].mapping_type == MappingType.DECOMPOSITION
    assert "bad source path" not in by_source


def test_extract_markdown_table_candidates_skips_headers_and_marks_conditionals() -> (
    None
):
    text = "\n".join(
        [
            "| source | target |",
            "| --- | --- |",
            "| dc:title | dcterms:title |",
            "| dc:type@lang | dcterms:type |",
            "| dc:skip | not-a-target |",
        ]
    )
    candidates = extract_markdown_table_candidates(text)

    by_source = {candidate.source_path: candidate for candidate in candidates}
    assert by_source["dc:title"].mapping_type == MappingType.DIRECT
    assert by_source["dc:type@lang"].mapping_type == MappingType.CONDITIONAL
    assert all(candidate.extractor_name == "markdown_table" for candidate in candidates)
    assert "dc:skip" not in by_source
