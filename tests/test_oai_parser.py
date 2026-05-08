from pathlib import Path

from m2s3om_graph.oai.bridge import bridge_metadata_format
from m2s3om_graph.oai.parser import (
    parse_identifiers,
    parse_metadata_formats,
    parse_metadata_prefixes,
)
from m2s3om_graph.transform.parsers import (
    parse_datacite_xml_to_ir,
    parse_marcxml_to_ir,
    parse_oai_dc_xml_to_ir,
)


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


def test_bridge_marcxml_by_namespace() -> None:
    xml_text = """
    <OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/">
      <ListMetadataFormats>
        <metadataFormat>
          <metadataPrefix>oai_dc</metadataPrefix>
          <schema>http://www.loc.gov/standards/marcxml/schema/MARC21slim.xsd</schema>
          <metadataNamespace>http://www.loc.gov/MARC21/slim</metadataNamespace>
        </metadataFormat>
      </ListMetadataFormats>
    </OAI-PMH>
    """
    formats = parse_metadata_formats(xml_text)
    resolved = bridge_metadata_format(formats[0])
    assert resolved is not None
    assert resolved.internal_format == "marcxml"
    assert resolved.source_profile == "marcxml"


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


def test_parse_marcxml_record_reads_field_and_subfield_keys() -> None:
    xml_text = """
    <record xmlns="http://www.loc.gov/MARC21/slim">
      <datafield tag="245" ind1="1" ind2="0">
        <subfield code="a">Example title</subfield>
        <subfield code="b">subtitle</subfield>
      </datafield>
      <datafield tag="856" ind1="4" ind2="0">
        <subfield code="u">https://example.org/item</subfield>
      </datafield>
    </record>
    """
    ir = parse_marcxml_to_ir(xml_text)
    assert ir["MARC 245"][0].text == "Example title subtitle"
    assert ir["MARC 245$a"][0].text == "Example title"
    assert ir["MARC 245$a$b"][0].text == "Example title subtitle"
    assert ir["MARC 856$u"][0].text == "https://example.org/item"
