from kaigraph.db import MappingRuleRecord, MappingType
from kaigraph.transform.apply import apply_mapping_rules
from kaigraph.transform.ir import IRValue, add_ir_value


def test_apply_direct_missing_and_conditional_rules() -> None:
    source_ir: dict[str, list[IRValue]] = {}
    add_ir_value(source_ir, "publicationYear", IRValue(text="2025"))
    add_ir_value(source_ir, "relationType", IRValue(text="isPartOf"))
    add_ir_value(source_ir, "relatedIdentifier", IRValue(text="doi:10.1/xyz"))

    rules = [
        MappingRuleRecord(
            id="r1",
            crosswalk_id="cw",
            source_paths=["publicationYear"],
            target_paths=["dcterms:issued"],
            mapping_type=MappingType.DIRECT,
            confidence=1.0,
            transform={"op": "copy"},
        ),
        MappingRuleRecord(
            id="r2",
            crosswalk_id="cw",
            source_paths=["identifierType"],
            target_paths=[],
            mapping_type=MappingType.MISSING,
            confidence=1.0,
            semantic_loss=True,
            transform={"op": "drop"},
        ),
        MappingRuleRecord(
            id="r3",
            crosswalk_id="cw",
            source_paths=["relatedIdentifier"],
            target_paths=["dcterms:relation"],
            mapping_type=MappingType.CONDITIONAL,
            confidence=0.8,
            transform={
                "op": "value_map",
                "field": "relationType",
                "mapping": {"isPartOf": "dcterms:isPartOf"},
                "default": "dcterms:relation",
            },
        ),
    ]

    target_ir, report = apply_mapping_rules(source_ir, rules)
    assert target_ir["dcterms:issued"][0].text == "2025"
    assert target_ir["dcterms:isPartOf"][0].text == "doi:10.1/xyz"
    assert "r2" in report.semantic_loss_rules
