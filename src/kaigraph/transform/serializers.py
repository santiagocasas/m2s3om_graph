import xml.etree.ElementTree as ET

from .ir import IRRecord
from .xml_namespaces import (
    DATACITE_NS,
    DATACITE_SCHEMA_LOCATION,
    DC_ELEMENTS_NS,
    DCTERMS_NS,
    OAI_DC_NS,
    OAI_DC_SCHEMA_LOCATION,
    XSI_NS,
)


def ir_to_dublin_core_xml(ir: IRRecord) -> str:
    root = ET.Element(
        "oai_dc:dc",
        {
            "xmlns:oai_dc": OAI_DC_NS,
            "xmlns:dc": DC_ELEMENTS_NS,
            "xmlns:dcterms": DCTERMS_NS,
            "xmlns:xsi": XSI_NS,
            "xsi:schemaLocation": OAI_DC_SCHEMA_LOCATION,
        },
    )

    seen_values: set[tuple[str, str, str]] = set()
    for key, values in ir.items():
        if ":" not in key:
            continue
        prefix, local = key.split(":", 1)
        if prefix not in {"dc", "dcterms"}:
            continue
        tag = f"{prefix}:{local}"
        for value in values:
            marker = (tag, value.text, value.lang or "")
            if marker in seen_values:
                continue
            seen_values.add(marker)
            node = ET.SubElement(root, tag)
            node.text = value.text
    return ET.tostring(root, encoding="unicode")


def ir_to_datacite_xml(ir: IRRecord) -> str:
    root = ET.Element(
        "resource",
        {
            "xmlns": DATACITE_NS,
            "xmlns:xsi": XSI_NS,
            "xsi:schemaLocation": DATACITE_SCHEMA_LOCATION,
        },
    )

    identifiers = ET.SubElement(root, "identifier")
    id_values = (
        ir.get("Identifier")
        or ir.get("identifier")
        or ir.get("dcterms:identifier")
        or ir.get("dc:identifier")
    )
    if id_values:
        identifiers.text = id_values[0].text
        identifiers.set(
            "identifierType", id_values[0].attrs.get("identifierType", "DOI")
        )

    titles = ET.SubElement(root, "titles")
    title = ET.SubElement(titles, "title")
    title_values = (
        ir.get("Title")
        or ir.get("title")
        or ir.get("dcterms:title")
        or ir.get("dc:title")
    )
    if title_values:
        title.text = title_values[0].text

    creators_values = (
        ir.get("Creator")
        or ir.get("creatorName")
        or ir.get("dcterms:creator")
        or ir.get("dc:creator")
    )
    creators = ET.SubElement(root, "creators")
    for creator_value in creators_values or []:
        creator = ET.SubElement(creators, "creator")
        creator_name = ET.SubElement(creator, "creatorName")
        creator_name.text = creator_value.text

    year_values = (
        ir.get("publicationYear")
        or ir.get("Date")
        or ir.get("dcterms:issued")
        or ir.get("dcterms:date")
        or ir.get("dc:date")
    )
    if year_values:
        year = ET.SubElement(root, "publicationYear")
        value = year_values[0].text.strip()
        year.text = value[:4] if len(value) >= 4 else value

    return ET.tostring(root, encoding="unicode")
