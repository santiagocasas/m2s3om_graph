from kaigraph.oai import load_demo_identifiers, load_institution_endpoints


def test_load_institution_endpoints_includes_dlr() -> None:
    institutions = load_institution_endpoints()
    by_name = {item.name: item.oai_endpoint for item in institutions}
    assert by_name["DLR"] == "https://elib.dlr.de/cgi/oai2"


def test_load_demo_identifiers_includes_dlr_samples() -> None:
    samples = load_demo_identifiers()
    assert "DLR" in samples
    assert "oai_dc" in samples["DLR"]
    assert "oai:elib.dlr.de:19460" in samples["DLR"]["oai_dc"]
