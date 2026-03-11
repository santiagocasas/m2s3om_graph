from dataclasses import dataclass
import xml.etree.ElementTree as ET

NS = {"oai": "http://www.openarchives.org/OAI/2.0/"}


@dataclass(frozen=True)
class MetadataFormatInfo:
    metadata_prefix: str
    schema: str
    metadata_namespace: str


@dataclass(frozen=True)
class IdentifierList:
    identifiers: list[str]
    resumption_token: str | None = None


def parse_metadata_formats(xml_text: str) -> list[MetadataFormatInfo]:
    root = ET.fromstring(xml_text)
    formats: list[MetadataFormatInfo] = []
    for node in root.findall(".//oai:metadataFormat", NS):
        metadata_prefix = node.findtext(
            "oai:metadataPrefix", default="", namespaces=NS
        ).strip()
        schema = node.findtext("oai:schema", default="", namespaces=NS).strip()
        metadata_namespace = node.findtext(
            "oai:metadataNamespace", default="", namespaces=NS
        ).strip()
        if metadata_prefix:
            formats.append(
                MetadataFormatInfo(
                    metadata_prefix=metadata_prefix,
                    schema=schema,
                    metadata_namespace=metadata_namespace,
                )
            )
    return formats


def parse_metadata_prefixes(xml_text: str) -> list[str]:
    return [item.metadata_prefix for item in parse_metadata_formats(xml_text)]


def parse_identifiers(xml_text: str, *, limit: int = 20) -> IdentifierList:
    root = ET.fromstring(xml_text)
    identifiers: list[str] = []
    for node in root.findall(".//oai:header/oai:identifier", NS):
        text = (node.text or "").strip()
        if text:
            identifiers.append(text)
        if len(identifiers) >= limit:
            break

    token = root.findtext(".//oai:resumptionToken", default="", namespaces=NS).strip()
    return IdentifierList(
        identifiers=identifiers,
        resumption_token=token or None,
    )
