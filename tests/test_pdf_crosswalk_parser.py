from pathlib import Path

from m2s3om_graph.ingest.pdf_crosswalk_parser import parse_mapping_page_texts


def test_parser_extracts_expected_rows() -> None:
    page_text = """
ID DataCite‐Property Dublin Core
5 publicationYear dcterms:issued
1.a identifierType Not present in Dublin Core
12.b relationTypeii
isPartOf dcterms:isPartOf
Other relation types dcterms:relation
"""
    rows = parse_mapping_page_texts([page_text], doc_uri="file:///tmp/mapping.pdf")

    by_id = {row.row_id: row for row in rows}
    assert "5" in by_id
    assert by_id["5"].dublin_core == "dcterms:issued"

    assert "1.a" in by_id
    assert by_id["1.a"].dublin_core == "Not present in Dublin Core"

    assert "12.b" in by_id
    relation = by_id["12.b"]
    assert relation.mapping_type.value == "conditional"
    assert any(
        case.key == "isPartOf" and case.value == "dcterms:isPartOf"
        for case in relation.cases
    )


def test_real_pdf_is_parsable_if_available(datacite_mapping_pdf_path: Path) -> None:
    from m2s3om_graph.ingest.pdf_crosswalk_parser import parse_mapping_pdf

    rows = parse_mapping_pdf(datacite_mapping_pdf_path)
    assert len(rows) > 20
