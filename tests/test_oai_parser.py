from pathlib import Path

from kaigraph.oai import parse_metadata_prefixes
from kaigraph.transform import parse_oai_dc_xml_to_ir


def test_parse_metadata_formats_fixture() -> None:
    xml_text = Path("tests/fixtures/oai_list_formats.xml").read_text(encoding="utf-8")
    prefixes = parse_metadata_prefixes(xml_text)
    assert "oai_dc" in prefixes
    assert "datacite" in prefixes


def test_parse_oai_dc_record_fixture() -> None:
    xml_text = Path("tests/fixtures/oai_getrecord_dc.xml").read_text(encoding="utf-8")
    ir = parse_oai_dc_xml_to_ir(xml_text)
    assert ir["dc:title"][0].text == "Sample DLR dataset title"
    assert ir["dc:creator"][0].text == "Doe, Jane"
    assert ir["dcterms:issued"][0].text == "2024"
