from pathlib import Path

from kaigraph.oai import (
    bridge_metadata_format,
    parse_identifiers,
    parse_metadata_formats,
    parse_metadata_prefixes,
)
from kaigraph.transform import parse_datacite_xml_to_ir, parse_oai_dc_xml_to_ir


def test_parse_metadata_formats_fixture() -> None:
    xml_text = Path("tests/fixtures/oai_list_formats.xml").read_text(encoding="utf-8")
    prefixes = parse_metadata_prefixes(xml_text)
    assert "oai_dc" in prefixes
    assert "datacite" in prefixes

    formats = parse_metadata_formats(xml_text)
    assert formats[0].metadata_prefix == "oai_dc"
    assert formats[1].metadata_namespace == "http://datacite.org/schema/kernel-4"


def test_bridge_oai_openaire_as_datacite() -> None:
    xml_text = """
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
      <ListMetadataFormats>
        <metadataFormat>
          <metadataPrefix>oai_openaire</metadataPrefix>
          <schema>https://www.openaire.eu/schema/oaire-4.0/oaire.xsd</schema>
          <metadataNamespace>http://namespace.openaire.eu/schema/oaire/</metadataNamespace>
        </metadataFormat>
      </ListMetadataFormats>
    </OAI-PMH>
    """
    formats = parse_metadata_formats(xml_text)
    resolved = bridge_metadata_format(formats[0])
    assert resolved is not None
    assert resolved.internal_format == "datacite_xml"
    assert resolved.source_profile == "oai_openaire"


def test_parse_identifiers_fixture() -> None:
    xml_text = """
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
      <ListIdentifiers>
        <header><identifier>oai:example.org:1</identifier></header>
        <header><identifier>oai:example.org:2</identifier></header>
        <resumptionToken>abc</resumptionToken>
      </ListIdentifiers>
    </OAI-PMH>
    """
    result = parse_identifiers(xml_text)
    assert result.identifiers == ["oai:example.org:1", "oai:example.org:2"]
    assert result.resumption_token == "abc"


def test_parse_oai_dc_record_fixture() -> None:
    xml_text = Path("tests/fixtures/oai_getrecord_dc.xml").read_text(encoding="utf-8")
    ir = parse_oai_dc_xml_to_ir(xml_text)
    assert ir["dc:title"][0].text == "Sample DLR dataset title"
    assert ir["dc:creator"][0].text == "Doe, Jane"
    assert ir["dcterms:issued"][0].text == "2024"


def test_parse_datacite_record_reads_title() -> None:
    xml_text = """
    <resource xmlns="http://datacite.org/schema/kernel-4">
      <identifier identifierType="DOI">10.1234/example</identifier>
      <titles><title>Example title</title></titles>
      <creators><creator><creatorName>Example, Alice</creatorName></creator></creators>
      <publicationYear>2024</publicationYear>
    </resource>
    """
    ir = parse_datacite_xml_to_ir(xml_text)
    assert ir["datacite:title"][0].text == "Example title"
    assert ir["Title"][0].text == "Example title"
