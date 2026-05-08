from typing import Any

from defusedxml import ElementTree as ET

import requests

from m2s3om_graph.interop.constants import (
    DATACITE_NS,
    ELIB_DC_EXPORT_TEMPLATE,
    ELIB_OPENAIRE_EXPORT_TEMPLATE,
    OAIRE_NS,
)
from m2s3om_graph.transform.ir import IRRecord, IRValue, add_ir_value

NS = {
    "datacite": DATACITE_NS,
    "oaire": OAIRE_NS,
}

DC_EXPORT_ALIAS_KEYS: dict[str, list[str]] = {
    "title": ["Title", "title"],
    "creator": ["Creator", "creatorName"],
    "identifier": ["Identifier", "identifier"],
    "date": ["Date"],
    "subject": ["subject"],
    "relation": ["relatedIdentifier"],
}


def elib_export_urls(record_id: str) -> dict[str, str]:
    clean = record_id.strip().strip("/")
    if clean.startswith("oai:elib.dlr.de:"):
        clean = clean.split(":")[-1]
    return {
        "openaire": ELIB_OPENAIRE_EXPORT_TEMPLATE.format(record_id=clean),
        "dublin_core": ELIB_DC_EXPORT_TEMPLATE.format(record_id=clean),
    }


def fetch_export(url: str, timeout_s: int = 20) -> str:
    response = requests.get(url, timeout=timeout_s)
    response.raise_for_status()
    return response.text


def _add_dc_export_alias_values(ir: IRRecord, key: str, value: str) -> None:
    for alias in DC_EXPORT_ALIAS_KEYS.get(key, []):
        add_ir_value(ir, alias, IRValue(text=value))
    if key == "date" and len(value) >= 4 and value[:4].isdigit():
        add_ir_value(ir, "publicationYear", IRValue(text=value[:4]))


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
        _add_dc_export_alias_values(ir, key, value)
    return ir


def _add_openaire_titles(ir: IRRecord, root: Any) -> None:
    for node in root.findall(".//datacite:title", NS):
        text = (node.text or "").strip()
        if not text:
            continue
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


def _add_openaire_creators(ir: IRRecord, root: Any) -> None:
    for node in root.findall(".//datacite:creatorName", NS):
        text = (node.text or "").strip()
        if not text:
            continue
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


def _add_openaire_identifiers(ir: IRRecord, root: Any) -> None:
    for node in root.findall(".//datacite:identifier", NS):
        text = (node.text or "").strip()
        if not text:
            continue
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


def _add_openaire_dates(ir: IRRecord, root: Any) -> None:
    for node in root.findall(".//datacite:date", NS):
        text = (node.text or "").strip()
        if not text:
            continue
        add_ir_value(
            ir,
            "Date",
            IRValue(text=text, attrs={"dateType": node.attrib.get("dateType", "")}),
        )
        if len(text) >= 4 and text[:4].isdigit():
            add_ir_value(ir, "publicationYear", IRValue(text=text[:4]))


def _add_openaire_resource_types(ir: IRRecord, root: Any) -> None:
    for node in root.findall(".//oaire:resourceType", NS):
        text = (node.text or "").strip()
        if text:
            add_ir_value(ir, "resourceType", IRValue(text=text))


def parse_openaire_xml_to_ir(xml_text: str) -> IRRecord:
    root = ET.fromstring(xml_text)
    ir: IRRecord = {}

    _add_openaire_titles(ir, root)
    _add_openaire_creators(ir, root)
    _add_openaire_identifiers(ir, root)
    _add_openaire_dates(ir, root)
    _add_openaire_resource_types(ir, root)
    return ir
