from kaigraph.db import (
    CrosswalkBundle,
    CrosswalkRecord,
    MappingRuleRecord,
    MappingType,
    StandardRecord,
)
from kaigraph.sssom import bundle_to_sssom_tsv, sssom_tsv_to_rules


def test_sssom_roundtrip_preserves_rule_core_fields() -> None:
    bundle = CrosswalkBundle(
        crosswalk=CrosswalkRecord(
            id="cw:test",
            name="Test",
            source_standard_id="src",
            target_standard_id="dst",
        ),
        source_standard=StandardRecord(id="src", name="Source"),
        target_standard=StandardRecord(id="dst", name="Target"),
        rules=[
            MappingRuleRecord(
                id="r1",
                crosswalk_id="cw:test",
                source_paths=["a"],
                target_paths=["b"],
                mapping_type=MappingType.DIRECT,
                confidence=0.9,
                transform={"op": "copy"},
            ),
            MappingRuleRecord(
                id="r2",
                crosswalk_id="cw:test",
                source_paths=["x"],
                target_paths=[],
                mapping_type=MappingType.MISSING,
                confidence=1.0,
                semantic_loss=True,
                transform={"op": "drop"},
            ),
        ],
    )

    tsv = bundle_to_sssom_tsv(bundle)
    parsed = sssom_tsv_to_rules(tsv, "cw:test")

    by_id = {rule.id: rule for rule in parsed}
    assert by_id["r1"].source_paths == ["a"]
    assert by_id["r1"].target_paths == ["b"]
    assert by_id["r1"].mapping_type == MappingType.DIRECT
    assert by_id["r2"].mapping_type == MappingType.MISSING
    assert by_id["r2"].semantic_loss is True
