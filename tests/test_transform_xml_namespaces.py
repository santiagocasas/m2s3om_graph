from kaigraph.transform import xml_namespaces


def test_http_url_builds_expected_shape() -> None:
    assert (
        xml_namespaces._http_url("example.org", "path/to/resource")
        == "http://example.org/path/to/resource"
    )
    assert (
        xml_namespaces._http_url("example.org", "/already/trimmed")
        == "http://example.org/already/trimmed"
    )


def test_namespace_and_schema_location_constants_are_consistent() -> None:
    assert xml_namespaces.OAI_DC_NS.startswith("http://")
    assert xml_namespaces.OAI_PMH_NS.startswith("http://")
    assert xml_namespaces.DC_ELEMENTS_NS.startswith("http://")
    assert xml_namespaces.DCTERMS_NS.startswith("http://")
    assert xml_namespaces.XSI_NS.startswith("http://")
    assert xml_namespaces.DATACITE_NS.startswith("http://")

    assert xml_namespaces.OAI_DC_SCHEMA_LOCATION.startswith(
        f"{xml_namespaces.OAI_DC_NS} "
    )
    assert xml_namespaces.OAI_DC_SCHEMA_LOCATION.endswith("oai_dc.xsd")

    assert xml_namespaces.DATACITE_SCHEMA_LOCATION.startswith(
        f"{xml_namespaces.DATACITE_NS} "
    )
    assert xml_namespaces.DATACITE_SCHEMA_LOCATION.endswith("metadata.xsd")
