from kaigraph.db import MappingType
from kaigraph.ingest.deterministic.engine import extract_deterministic_candidates


def test_extract_deterministic_candidates_assignment_and_dedupe() -> None:
    text = """
    titleproper = E35 Title
    titleproper = E35 Title
    unitdate@normal = E52 Time-Span
    """
    candidates, diagnostics = extract_deterministic_candidates(text)

    assert diagnostics.candidates_before_dedupe >= 2
    assert diagnostics.candidates_after_dedupe == 2

    by_source = {x.source_path: x for x in candidates}
    assert by_source["titleproper"].mapping_type == MappingType.DIRECT
    assert by_source["unitdate@normal"].mapping_type == MappingType.CONDITIONAL


def test_extract_deterministic_candidates_markdown_table() -> None:
    text = """
    | source term | target term |
    | --- | --- |
    | dc:title | dcterms:title |
    | dc:creator | dcterms:creator |
    """
    candidates, diagnostics = extract_deterministic_candidates(text)

    assert diagnostics.extractor_counts["markdown_table"] >= 2
    assert any(x.source_path == "dc:title" for x in candidates)


def test_extract_deterministic_candidates_rtf_like_text() -> None:
    text = (
        "{\\i\\lang1033 titleproper }{\\lang1033 = E35 Title}\\par\n"
        "{\\lang1033 ead = E31 Document}\\par\n"
        "{\\lang1033 archdesc = E22 Man-Made Object}"
    )
    candidates, _ = extract_deterministic_candidates(text)

    assert len(candidates) >= 3
    assert all(x.mapping_type in MappingType for x in candidates)
