from kaigraph.ingestion.extractor import extract_elements_from_text


def test_extract_elements_from_text() -> None:
    text = """
dc.title - Name of resource. cardinality 1..1 type string
dc.date - Date associated with resource. cardinality 0..n type date
"""
    result = extract_elements_from_text("dc", text)
    assert len(result.elements) == 2
    assert result.elements[0].id == "dc:dc.title"
    assert result.elements[1].path == "dc.date"


def test_extract_marc_subfield_paths() -> None:
    text = "245$a - Title statement text of the resource. cardinality 1..1 type string"
    result = extract_elements_from_text("marcxml", text)
    assert len(result.elements) == 1
    assert result.elements[0].path == "245$a"
