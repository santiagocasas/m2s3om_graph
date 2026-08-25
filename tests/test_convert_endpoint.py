"""Behavioral tests for the /convert endpoint in server/main.py.

Regression coverage for a bug where /convert silently echoed the source XML
back unchanged (reporting 0 applied rules) instead of erroring when no
crosswalk or no serializer was available for the requested conversion.
"""

from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)

VALID_DATACITE_XML = """
<resource
  xmlns:resource="http://datacite.org/schema/kernel-4">
  <resource:identifier identifierType="DOI">10.1234/example</resource:identifier>
  <resource:title>Example Title</resource:title>
  <resource:creator>
    <resource:creatorName>Example, Alice</resource:creatorName>
  </resource:creator>
  <resource:publicationYear>2024</resource:publicationYear>
</resource>
"""


def test_convert_rejects_unsupported_source_format() -> None:
    resp = client.post(
        "/convert",
        json={
            "source_xml": "<x/>",
            "source_format": "openaire_xml",
            "target_format": "datacite_xml",
        },
    )
    assert resp.status_code == 400
    assert "Unsupported source format" in resp.json()["detail"]


def test_convert_rejects_target_format_without_serializer() -> None:
    """MARC has a parser but no serializer; it must fail loudly, not echo input."""
    resp = client.post(
        "/convert",
        json={
            "source_xml": VALID_DATACITE_XML,
            "source_format": "datacite_xml",
            "target_format": "marcxml",
        },
    )
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    assert "no serializer" in detail
    assert "marcxml" in detail


def test_convert_rejects_malformed_source_xml() -> None:
    resp = client.post(
        "/convert",
        json={
            "source_xml": "<oaire:resource>not namespaced</oaire:resource>",
            "source_format": "datacite_xml",
            "target_format": "oai_dc_xml",
        },
    )
    assert resp.status_code == 400
    assert "Failed to parse source XML" in resp.json()["detail"]


def test_convert_returns_404_when_no_crosswalk_exists() -> None:
    """datacite44 -> datacite44 has no self-crosswalk in the graph."""
    resp = client.post(
        "/convert",
        json={
            "source_xml": VALID_DATACITE_XML,
            "source_format": "datacite_xml",
            "target_format": "datacite_xml",
        },
    )
    assert resp.status_code == 404
    assert "No crosswalk found" in resp.json()["detail"]


def test_convert_datacite_to_oai_dc_applies_real_crosswalk_rules() -> None:
    """The one real crosswalk (datacite44 <-> dcterms) must actually apply rules."""
    resp = client.post(
        "/convert",
        json={
            "source_xml": VALID_DATACITE_XML,
            "source_format": "datacite_xml",
            "target_format": "oai_dc_xml",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["applied_rule_ids"]) > 0
    assert "Example Title" in data["target_xml"]
    assert "dcterms:title" in data["target_xml"]
