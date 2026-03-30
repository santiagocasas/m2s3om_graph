from kaigraph.interop.elib import (
    elib_export_urls,
    parse_dc_export_text_to_ir,
    parse_openaire_xml_to_ir,
)


def test_elib_url_builder() -> None:
    urls = elib_export_urls("204960")
    assert urls["openaire"].endswith("/204960/OPENAIRE/dlr-eprint-204960.xml")
    assert urls["dublin_core"].endswith("/204960/DC/dlr-eprint-204960.txt")


def test_parse_dc_export_text() -> None:
    text = """
title: Example title
creator: Example author
identifier: 10.000/test
"""
    ir = parse_dc_export_text_to_ir(text)
    assert ir["dcterms:title"][0].text == "Example title"
    assert ir["dcterms:creator"][0].text == "Example author"
    assert ir["Title"][0].text == "Example title"


def test_parse_openaire_xml() -> None:
    xml_text = """
<oaire:resource xmlns:oaire="http://namespace.openaire.eu/schema/oaire/" xmlns:datacite="http://datacite.org/schema/kernel-4">
  <datacite:titles>
    <datacite:title>Example title</datacite:title>
  </datacite:titles>
  <datacite:creators>
    <datacite:creator><datacite:creatorName>A. Author</datacite:creatorName></datacite:creator>
  </datacite:creators>
  <datacite:identifier>10.000/test</datacite:identifier>
</oaire:resource>
"""
    ir = parse_openaire_xml_to_ir(xml_text)
    assert ir["Title"][0].text == "Example title"
    assert ir["Creator"][0].text == "A. Author"
    assert ir["Identifier"][0].text == "10.000/test"
    assert ir["title"][0].text == "Example title"
