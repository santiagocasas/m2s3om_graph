from typing import Any

from defusedxml import ElementTree as ET

from .ir import IRRecord, IRValue, add_ir_value
from .xml_namespaces import (
    DATACITE_NS,
    DC_ELEMENTS_NS,
    DCTERMS_NS,
    OAI_DC_NS,
    OAI_PMH_NS,
)

NS_OAI = {
    "oai_dc": OAI_DC_NS,
    "dc": DC_ELEMENTS_NS,
    "dcterms": DCTERMS_NS,
}
NS_DATACITE = {"resource": DATACITE_NS}
NS_MARC = {"marc": "http://www.loc.gov/MARC21/slim"}
DATACITE_RESOURCE_TAG = f"{{{DATACITE_NS}}}resource"
OAI_IDENTIFIER_PATH = f".//{{{OAI_PMH_NS}}}identifier"


def _find_datacite_resource(root: Any) -> Any:
    if root.tag == DATACITE_RESOURCE_TAG:
        return root
    nested = root.find(".//resource:resource", NS_DATACITE)
    if nested is not None:
        return nested
    return root


def parse_oai_dc_xml_to_ir(xml_text: str) -> IRRecord:
    root = ET.fromstring(xml_text)
    ir: IRRecord = {}
    source_id_node = root.find(OAI_IDENTIFIER_PATH)
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
    root = _find_datacite_resource(ET.fromstring(xml_text))
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

    for title in root.findall(".//resource:title", NS_DATACITE):
        title_text = (title.text or "").strip()
        if title_text:
            add_ir_value(
                ir,
                "datacite:title",
                IRValue(
                    text=title_text,
                    source_path="datacite:title",
                    source_format="datacite",
                ),
            )
            add_ir_value(ir, "Title", IRValue(text=title_text))
            add_ir_value(ir, "title", IRValue(text=title_text))

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


def parse_marcxml_to_ir(xml_text: str) -> IRRecord:
    root = ET.fromstring(xml_text)
    ir: IRRecord = {}

    for field in root.findall(".//marc:datafield", NS_MARC):
        tag = field.attrib.get("tag", "").strip()
        if not tag:
            continue

        subfields: dict[str, list[str]] = {}
        for subfield in field.findall("marc:subfield", NS_MARC):
            code = subfield.attrib.get("code", "").strip()
            text = (subfield.text or "").strip()
            if not code or not text:
                continue
            subfields.setdefault(code, []).append(text)
            add_ir_value(
                ir,
                f"MARC {tag}${code}",
                IRValue(
                    text=text,
                    source_path=f"MARC {tag}${code}",
                    source_format="marcxml",
                ),
            )

        if subfields:
            joined = " ".join(
                text for code in sorted(subfields) for text in subfields[code]
            ).strip()
            if joined:
                add_ir_value(
                    ir,
                    f"MARC {tag}",
                    IRValue(
                        text=joined,
                        source_path=f"MARC {tag}",
                        source_format="marcxml",
                    ),
                )

        subfield_codes = sorted(subfields)
        if len(subfield_codes) > 1:
            combined_key = f"MARC {tag}$" + "$".join(subfield_codes)
            combined_text = " ".join(
                text for code in subfield_codes for text in subfields[code]
            ).strip()
            if combined_text:
                add_ir_value(
                    ir,
                    combined_key,
                    IRValue(
                        text=combined_text,
                        source_path=combined_key,
                        source_format="marcxml",
                    ),
                )

    return ir
