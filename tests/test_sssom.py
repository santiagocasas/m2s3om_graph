import csv
import io

from m2s3om_graph.db import (
    CrosswalkBundle,
    CrosswalkRecord,
    MappingRuleRecord,
    MappingType,
    StandardRecord,
)
from m2s3om_graph.sssom import bundle_to_sssom_tsv, sssom_tsv_to_rules


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


def test_sssom_justification_uses_only_ambiguity_signal() -> None:
    bundle = CrosswalkBundle(
        crosswalk=CrosswalkRecord(
            id="cw:justifications",
            name="Justifications",
            source_standard_id="src",
            target_standard_id="dst",
        ),
        source_standard=StandardRecord(id="src", name="Source"),
        target_standard=StandardRecord(id="dst", name="Target"),
        rules=[
            MappingRuleRecord(
                id="r_direct",
                crosswalk_id="cw:justifications",
                source_paths=["a"],
                target_paths=["b"],
                mapping_type=MappingType.DIRECT,
                confidence=0.9,
                ambiguity=False,
                transform={"op": "copy"},
            ),
            MappingRuleRecord(
                id="r_missing",
                crosswalk_id="cw:justifications",
                source_paths=["x"],
                target_paths=[],
                mapping_type=MappingType.MISSING,
                confidence=1.0,
                ambiguity=False,
                transform={"op": "drop"},
            ),
            MappingRuleRecord(
                id="r_ambiguous",
                crosswalk_id="cw:justifications",
                source_paths=["m"],
                target_paths=["n"],
                mapping_type=MappingType.CONDITIONAL,
                confidence=0.7,
                ambiguity=True,
                transform={"op": "copy"},
            ),
        ],
    )

    tsv = bundle_to_sssom_tsv(bundle)
    rows = [line for line in tsv.splitlines() if line and not line.startswith("#")]
    parsed = csv.DictReader(io.StringIO("\n".join(rows)), delimiter="\t")
    by_id = {row["record_id"]: row for row in parsed}

    assert by_id["r_direct"]["mapping_justification"] == "semapv:ManualMappingCuration"
    assert by_id["r_missing"]["mapping_justification"] == "semapv:ManualMappingCuration"
    assert by_id["r_ambiguous"]["mapping_justification"] == "semapv:CompositeMatching"
