from kaigraph.transform import IRValue, ir_to_datacite_xml


def test_datacite_serializer_accepts_common_alias_keys() -> None:
    ir = {
        "identifier": [IRValue(text="10.1234/example")],
        "title": [IRValue(text="Example title")],
        "creatorName": [IRValue(text="Example, Alice")],
        "publicationYear": [IRValue(text="2024")],
    }
    xml = ir_to_datacite_xml(ir)
    assert "<identifier" in xml
    assert "Example title" in xml
    assert "creatorName" in xml
    assert "<publicationYear>2024</publicationYear>" in xml
