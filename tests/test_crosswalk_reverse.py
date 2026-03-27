from kaigraph.crosswalk.reverse import _reverse_target_paths, derive_reverse_rules
from kaigraph.db import CrosswalkBundle, CrosswalkRecord, MappingRuleRecord, MappingType
from kaigraph.db.models import StandardRecord


def _forward_bundle() -> CrosswalkBundle:
    return CrosswalkBundle(
        crosswalk=CrosswalkRecord(
            id="cw_forward",
            name="Forward",
            source_standard_id="src",
            target_standard_id="tgt",
        ),
        source_standard=StandardRecord(id="src", name="Source"),
        target_standard=StandardRecord(id="tgt", name="Target"),
        rules=[
            MappingRuleRecord(
                id="rule_1",
                crosswalk_id="cw_forward",
                source_element_id="src:title",
                source_paths=["title", "1alt"],
                target_element_id="tgt:title",
                target_paths=["dc:title"],
                mapping_type=MappingType.DIRECT,
                confidence=0.9,
                transform={"op": "copy"},
            ),
            MappingRuleRecord(
                id="rule_2",
                crosswalk_id="cw_forward",
                source_element_id="src:type",
                source_paths=["type"],
                target_element_id="tgt:type",
                target_paths=["dc:title"],
                mapping_type=MappingType.MISSING,
                confidence=0.8,
                transform={
                    "op": "value_map",
                    "mapping": {"A": "alpha"},
                    "default": "x",
                },
            ),
        ],
    )


def test_reverse_target_paths_prefers_non_numeric_source_paths() -> None:
    rule = MappingRuleRecord(
        id="r",
        crosswalk_id="c",
        source_paths=["1", "2"],
        target_paths=["dc:title"],
        mapping_type=MappingType.DIRECT,
        confidence=1.0,
        transform={"op": "copy"},
    )
    assert _reverse_target_paths(rule) == ["1", "2"]

    rule_with_preferred = rule.model_copy(update={"source_paths": ["title", "2"]})
    assert _reverse_target_paths(rule_with_preferred) == ["title"]


def test_derive_reverse_rules_marks_ambiguity_and_inverts_value_map() -> None:
    reverse_rules = derive_reverse_rules(_forward_bundle())
    assert len(reverse_rules) == 2

    by_source = {x.source_element_id: x for x in reverse_rules}
    first = by_source["tgt:title"]
    assert first.crosswalk_id == "reverse:cw_forward"
    assert first.ambiguity is True
    assert first.confidence == 0.65
    assert first.target_paths == ["title"]

    second = by_source["tgt:type"]
    assert second.semantic_loss is True
    assert second.transform["mapping"] == {"alpha": "A"}
    assert second.transform["default"] == "Other"
