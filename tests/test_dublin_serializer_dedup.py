from kaigraph.transform.ir import IRValue
from kaigraph.transform.serializers import ir_to_dublin_core_xml


def test_dublin_core_serializer_deduplicates_same_value() -> None:
    ir = {
        "dcterms:creator": [
            IRValue(text="Pesta, Dominik"),
            IRValue(text="Pesta, Dominik"),
            IRValue(text="Pesta, Dominik"),
        ],
        "dcterms:title": [
            IRValue(text="A title"),
            IRValue(text="A title"),
        ],
    }
    xml = ir_to_dublin_core_xml(ir)
    assert xml.count("<dcterms:creator>") == 1
    assert xml.count("<dcterms:title>") == 1
