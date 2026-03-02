from kaigraph.rdamsc.artifacts import _normalize_legacy_shifted_text


def test_normalize_legacy_shifted_text_decodes_shifted_pdf_snippet() -> None:
    encoded = "0DSSLQJ\x03RI\x03WKH\x03&,'2&\x03&50"
    decoded = _normalize_legacy_shifted_text(encoded)
    assert "Mapping" in decoded
    assert "the" in decoded


def test_normalize_legacy_shifted_text_leaves_normal_text_unchanged() -> None:
    text = "DataCite to Dublin Core Mapping 4.4"
    assert _normalize_legacy_shifted_text(text) == text
