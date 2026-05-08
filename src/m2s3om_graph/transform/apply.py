from dataclasses import dataclass, field
from typing import Callable

from m2s3om_graph.db import MappingRuleRecord, MappingType

from .ir import IRRecord, IRValue, add_ir_value, get_first_text


@dataclass
class TransformationReport:
    applied_rule_ids: list[str] = field(default_factory=list)
    unmapped_fields: list[str] = field(default_factory=list)
    semantic_loss_rules: list[str] = field(default_factory=list)
    ambiguous_rules: list[str] = field(default_factory=list)


def _values_for_source_paths(ir: IRRecord, source_paths: list[str]) -> list[IRValue]:
    def _value_key(
        value: IRValue,
    ) -> tuple[str, str | None, str | None, str | None, tuple[tuple[str, str], ...]]:
        return (
            value.text,
            value.lang,
            value.scheme,
            value.uri,
            tuple(sorted(value.attrs.items())),
        )

    values: list[IRValue] = []
    seen: set[
        tuple[str, str | None, str | None, str | None, tuple[tuple[str, str], ...]]
    ] = set()
    for source in source_paths:
        for key in (source, f"datacite:{source}", source.lower()):
            for value in ir.get(key, []):
                marker = _value_key(value)
                if marker in seen:
                    continue
                seen.add(marker)
                values.append(value)
    return values


def _output_keys_for_rule(rule: MappingRuleRecord) -> list[str]:
    output_keys = rule.target_paths[:]
    if not output_keys and rule.target_element_id:
        output_keys = [rule.target_element_id.split(":", 1)[-1]]
    return output_keys


def _apply_copy_rule(
    source_ir: IRRecord,
    target_ir: IRRecord,
    rule: MappingRuleRecord,
    output_keys: list[str],
) -> bool:
    source_values = _values_for_source_paths(source_ir, rule.source_paths)
    if not source_values:
        return False
    for output_key in output_keys:
        for value in source_values:
            add_ir_value(target_ir, output_key, value)
    return True


def _apply_concat_rule(
    source_ir: IRRecord,
    target_ir: IRRecord,
    rule: MappingRuleRecord,
    output_keys: list[str],
) -> bool:
    sep = str(rule.transform.get("separator", "; "))
    fields = rule.transform.get("sources", rule.source_paths)
    if not isinstance(fields, list):
        fields = rule.source_paths
    parts: list[str] = []
    for source_field in fields:
        if not isinstance(source_field, str):
            continue
        text = get_first_text(source_ir, source_field)
        if text:
            parts.append(text)
    if not parts or not output_keys:
        return False
    for output_key in output_keys:
        add_ir_value(target_ir, output_key, IRValue(text=sep.join(parts)))
    return True


def _apply_value_map_rule(
    source_ir: IRRecord,
    target_ir: IRRecord,
    rule: MappingRuleRecord,
    _output_keys: list[str],
) -> bool:
    mapping = rule.transform.get("mapping", {})
    field = str(rule.transform.get("field", ""))
    default = rule.transform.get("default")
    raw_value = get_first_text(source_ir, field) or get_first_text(
        source_ir,
        f"datacite:{field}",
    )
    if not isinstance(mapping, dict):
        mapping = {}
    target_term = None
    if raw_value is not None:
        for key, value in mapping.items():
            if str(key).lower() == raw_value.lower():
                target_term = str(value)
                break
    if target_term is None and default is not None:
        target_term = str(default)

    source_values = _values_for_source_paths(source_ir, rule.source_paths)
    if not target_term or not source_values:
        return False
    for value in source_values:
        add_ir_value(target_ir, target_term, value)
    return True


def _apply_split_rule(
    source_ir: IRRecord,
    target_ir: IRRecord,
    rule: MappingRuleRecord,
    output_keys: list[str],
) -> bool:
    source_values = _values_for_source_paths(source_ir, rule.source_paths)
    if not source_values or not output_keys:
        return False
    chunks = [x.strip() for x in source_values[0].text.split(";") if x.strip()]
    for idx, chunk in enumerate(chunks):
        key = output_keys[min(idx, len(output_keys) - 1)]
        add_ir_value(target_ir, key, IRValue(text=chunk))
    return True


def _apply_fallback_rule(
    source_ir: IRRecord,
    target_ir: IRRecord,
    rule: MappingRuleRecord,
    output_keys: list[str],
) -> bool:
    source_values = _values_for_source_paths(source_ir, rule.source_paths)
    if not source_values or not output_keys:
        return False
    for key in output_keys:
        for value in source_values:
            add_ir_value(target_ir, key, value)
    return True


RuleHandler = Callable[[IRRecord, IRRecord, MappingRuleRecord, list[str]], bool]


RULE_HANDLERS: dict[str, RuleHandler] = {
    "copy": _apply_copy_rule,
    "concat": _apply_concat_rule,
    "value_map": _apply_value_map_rule,
    "split": _apply_split_rule,
}


def _apply_rule_operation(
    source_ir: IRRecord,
    target_ir: IRRecord,
    rule: MappingRuleRecord,
    output_keys: list[str],
) -> bool:
    op = str(rule.transform.get("op", "copy"))
    handler = RULE_HANDLERS.get(op, _apply_fallback_rule)
    return handler(source_ir, target_ir, rule, output_keys)


def apply_mapping_rules(
    source_ir: IRRecord,
    rules: list[MappingRuleRecord],
) -> tuple[IRRecord, TransformationReport]:
    target_ir: IRRecord = {}
    report = TransformationReport()

    for rule in rules:
        if rule.semantic_loss:
            report.semantic_loss_rules.append(rule.id)
        if rule.ambiguity:
            report.ambiguous_rules.append(rule.id)

        output_keys = _output_keys_for_rule(rule)

        if rule.mapping_type == MappingType.MISSING:
            report.applied_rule_ids.append(rule.id)
            continue

        if _apply_rule_operation(source_ir, target_ir, rule, output_keys):
            report.applied_rule_ids.append(rule.id)
            continue
        report.unmapped_fields.extend(rule.source_paths)

    report.unmapped_fields = sorted(set(report.unmapped_fields))
    return target_ir, report
