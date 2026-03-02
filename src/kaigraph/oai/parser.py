import xml.etree.ElementTree as ET

NS = {"oai": "http://www.openarchives.org/OAI/2.0/"}


def parse_metadata_prefixes(xml_text: str) -> list[str]:
    root = ET.fromstring(xml_text)
    prefixes: list[str] = []
    for node in root.findall(".//oai:metadataFormat/oai:metadataPrefix", NS):
        text = (node.text or "").strip()
        if text:
            prefixes.append(text)
    return prefixes
