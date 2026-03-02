import xml.etree.ElementTree as ET

from .ir import IRRecord, IRValue, add_ir_value

NS_OAI = {
    "oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
    "dc": "http://purl.org/dc/elements/1.1/",
    "dcterms": "http://purl.org/dc/terms/",
}
NS_DATACITE = {"resource": "http://datacite.org/schema/kernel-4"}


def parse_oai_dc_xml_to_ir(xml_text: str) -> IRRecord:
    root = ET.fromstring(xml_text)
    ir: IRRecord = {}
    source_id_node = root.find(".//{http://www.openarchives.org/OAI/2.0/}identifier")
    source_id = (
        (source_id_node.text or "").strip() if source_id_node is not None else None
    )

    for node in root.findall(".//dc:*", NS_OAI):
        local_name = node.tag.split("}", 1)[-1]
        text = (node.text or "").strip()
        if text:
            add_ir_value(
                ir,
                f"dc:{local_name}",
                IRValue(
                    text=text,
                    source_record_id=source_id,
                    source_path=f"dc:{local_name}",
                    source_format="oai_dc",
                ),
            )

    for node in root.findall(".//dcterms:*", NS_OAI):
        local_name = node.tag.split("}", 1)[-1]
        text = (node.text or "").strip()
        if text:
            add_ir_value(
                ir,
                f"dcterms:{local_name}",
                IRValue(
                    text=text,
                    source_record_id=source_id,
                    source_path=f"dcterms:{local_name}",
                    source_format="oai_dc",
                ),
            )
    return ir


def parse_datacite_xml_to_ir(xml_text: str) -> IRRecord:
    root = ET.fromstring(xml_text)
    ir: IRRecord = {}

    identifier = root.find(".//resource:identifier", NS_DATACITE)
    if identifier is not None:
        identifier_text = (identifier.text or "").strip()
    else:
        identifier_text = ""
    if identifier is not None and identifier_text:
        add_ir_value(
            ir,
            "datacite:identifier",
            IRValue(
                text=identifier_text,
                attrs={"identifierType": identifier.attrib.get("identifierType", "")},
                source_path="datacite:identifier",
                source_format="datacite",
            ),
        )
        add_ir_value(ir, "Identifier", IRValue(text=identifier_text))

    for creator in root.findall(".//resource:creator", NS_DATACITE):
        name = creator.find("resource:creatorName", NS_DATACITE)
        name_text = (name.text or "").strip() if name is not None else ""
        if name is not None and name_text:
            add_ir_value(
                ir,
                "datacite:creatorName",
                IRValue(
                    text=name_text,
                    source_path="datacite:creatorName",
                    source_format="datacite",
                ),
            )
            add_ir_value(ir, "Creator", IRValue(text=name_text))
            add_ir_value(ir, "2.1", IRValue(text=name_text))

    publication_year = root.find(".//resource:publicationYear", NS_DATACITE)
    year_text = (
        (publication_year.text or "").strip() if publication_year is not None else ""
    )
    if publication_year is not None and year_text:
        add_ir_value(
            ir,
            "datacite:publicationYear",
            IRValue(
                text=year_text,
                source_path="datacite:publicationYear",
                source_format="datacite",
            ),
        )
        add_ir_value(ir, "publicationYear", IRValue(text=year_text))
        add_ir_value(ir, "5", IRValue(text=year_text))
    return ir
