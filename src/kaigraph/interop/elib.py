import xml.etree.ElementTree as ET

import requests

from kaigraph.transform import IRRecord, IRValue, add_ir_value

NS = {
    "datacite": "http://datacite.org/schema/kernel-4",
    "oaire": "http://namespace.openaire.eu/schema/oaire/",
}


def elib_export_urls(record_id: str) -> dict[str, str]:
    clean = record_id.strip().strip("/")
    if clean.startswith("oai:elib.dlr.de:"):
        clean = clean.split(":")[-1]
    return {
        "openaire": f"https://elib.dlr.de/cgi/export/eprint/{clean}/OPENAIRE/dlr-eprint-{clean}.xml",
        "dublin_core": f"https://elib.dlr.de/cgi/export/eprint/{clean}/DC/dlr-eprint-{clean}.txt",
    }


def fetch_export(url: str, timeout_s: int = 20) -> str:
    response = requests.get(url, timeout=timeout_s)
    response.raise_for_status()
    return response.text


def parse_dc_export_text_to_ir(text: str) -> IRRecord:
    ir: IRRecord = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if not value:
            continue
        target_key = f"dcterms:{key}"
        add_ir_value(
            ir,
            target_key,
            IRValue(
                text=value,
                source_path=target_key,
                source_format="dc_export",
            ),
        )
        if key == "title":
            add_ir_value(ir, "Title", IRValue(text=value))
            add_ir_value(ir, "title", IRValue(text=value))
        elif key == "creator":
            add_ir_value(ir, "Creator", IRValue(text=value))
            add_ir_value(ir, "creatorName", IRValue(text=value))
        elif key == "identifier":
            add_ir_value(ir, "Identifier", IRValue(text=value))
            add_ir_value(ir, "identifier", IRValue(text=value))
        elif key == "date":
            add_ir_value(ir, "Date", IRValue(text=value))
            if len(value) >= 4 and value[:4].isdigit():
                add_ir_value(ir, "publicationYear", IRValue(text=value[:4]))
        elif key == "subject":
            add_ir_value(ir, "subject", IRValue(text=value))
        elif key == "relation":
            add_ir_value(ir, "relatedIdentifier", IRValue(text=value))
    return ir


def parse_openaire_xml_to_ir(xml_text: str) -> IRRecord:
    root = ET.fromstring(xml_text)
    ir: IRRecord = {}

    for node in root.findall(".//datacite:title", NS):
        text = (node.text or "").strip()
        if text:
            add_ir_value(
                ir,
                "Title",
                IRValue(
                    text=text,
                    source_path="datacite:title",
                    source_format="openaire_xml",
                ),
            )
            add_ir_value(ir, "title", IRValue(text=text))

    for node in root.findall(".//datacite:creatorName", NS):
        text = (node.text or "").strip()
        if text:
            add_ir_value(
                ir,
                "Creator",
                IRValue(
                    text=text,
                    source_path="datacite:creatorName",
                    source_format="openaire_xml",
                ),
            )
            add_ir_value(ir, "creatorName", IRValue(text=text))
            add_ir_value(ir, "2.1", IRValue(text=text))

    for node in root.findall(".//datacite:identifier", NS):
        text = (node.text or "").strip()
        if text:
            add_ir_value(
                ir,
                "Identifier",
                IRValue(
                    text=text,
                    source_path="datacite:identifier",
                    source_format="openaire_xml",
                ),
            )
            add_ir_value(ir, "identifier", IRValue(text=text))

    for node in root.findall(".//datacite:date", NS):
        text = (node.text or "").strip()
        if text:
            add_ir_value(
                ir,
                "Date",
                IRValue(text=text, attrs={"dateType": node.attrib.get("dateType", "")}),
            )
            if len(text) >= 4 and text[:4].isdigit():
                add_ir_value(ir, "publicationYear", IRValue(text=text[:4]))

    for node in root.findall(".//oaire:resourceType", NS):
        text = (node.text or "").strip()
        if text:
            add_ir_value(ir, "resourceType", IRValue(text=text))
    return ir
