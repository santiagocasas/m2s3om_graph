from collections import defaultdict
from copy import deepcopy

from m2s3om_graph.db import CrosswalkBundle, MappingRuleRecord, MappingType, stable_id


def _reverse_target_paths(forward_rule: MappingRuleRecord) -> list[str]:
    preferred: list[str] = []
    for path in forward_rule.source_paths:
        if path and not path[0].isdigit():
            preferred.append(path)
    if preferred:
        return preferred
    return forward_rule.source_paths[:]


def derive_reverse_rules(forward: CrosswalkBundle) -> list[MappingRuleRecord]:
    by_target: dict[str, list[MappingRuleRecord]] = defaultdict(list)
    for rule in forward.rules:
        for target in rule.target_paths:
            by_target[target].append(rule)

    reverse_rules: list[MappingRuleRecord] = []
    reverse_crosswalk_id = f"reverse:{forward.crosswalk.id}"
    for target_path, rules in by_target.items():
        for idx, forward_rule in enumerate(rules):
            transform = deepcopy(forward_rule.transform)
            op = str(transform.get("op", "copy"))
            ambiguity = len(rules) > 1
            semantic_loss = forward_rule.mapping_type == MappingType.MISSING
            confidence = max(
                0.2, forward_rule.confidence - (0.25 if ambiguity else 0.0)
            )

            if op == "value_map":
                mapping = transform.get("mapping")
                if isinstance(mapping, dict):
                    transform["mapping"] = {str(v): str(k) for k, v in mapping.items()}
                if "default" in transform:
                    transform["default"] = "Other"

            reverse_rules.append(
                MappingRuleRecord(
                    id=stable_id(
                        "mapping_rule", reverse_crosswalk_id, target_path, str(idx)
                    ),
                    crosswalk_id=reverse_crosswalk_id,
                    source_element_id=forward_rule.target_element_id,
                    source_paths=[target_path],
                    target_element_id=forward_rule.source_element_id,
                    target_paths=_reverse_target_paths(forward_rule),
                    mapping_type=forward_rule.mapping_type,
                    confidence=confidence,
                    semantic_loss=semantic_loss,
                    ambiguity=ambiguity,
                    transform=transform,
                    evidence=forward_rule.evidence,
                    notes=(
                        "Derived reverse rule (best effort)."
                        " Information may be ambiguous or lossy."
                    ),
                )
            )
    return reverse_rules
