import xml.etree.ElementTree as ET

from .ir import IRRecord


def ir_to_dublin_core_xml(ir: IRRecord) -> str:
    root = ET.Element(
        "oai_dc:dc",
        {
            "xmlns:oai_dc": "http://www.openarchives.org/OAI/2.0/oai_dc/",
            "xmlns:dc": "http://purl.org/dc/elements/1.1/",
            "xmlns:dcterms": "http://purl.org/dc/terms/",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://www.openarchives.org/OAI/2.0/oai_dc/ http://www.openarchives.org/OAI/2.0/oai_dc.xsd",
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
            "xmlns": "http://datacite.org/schema/kernel-4",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
            "xsi:schemaLocation": "http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4.4/metadata.xsd",
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
