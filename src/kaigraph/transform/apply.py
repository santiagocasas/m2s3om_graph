from dataclasses import dataclass, field

from kaigraph.db import MappingRuleRecord, MappingType

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

        op = str(rule.transform.get("op", "copy"))
        output_keys = rule.target_paths[:]
        if not output_keys and rule.target_element_id:
            output_keys = [rule.target_element_id.split(":", 1)[-1]]

        if rule.mapping_type == MappingType.MISSING:
            report.applied_rule_ids.append(rule.id)
            continue

        if op == "copy":
            source_values = _values_for_source_paths(source_ir, rule.source_paths)
            if not source_values:
                report.unmapped_fields.extend(rule.source_paths)
                continue
            for output_key in output_keys:
                for value in source_values:
                    add_ir_value(target_ir, output_key, value)
            report.applied_rule_ids.append(rule.id)
            continue

        if op == "concat":
            sep = str(rule.transform.get("separator", "; "))
            fields = rule.transform.get("sources", rule.source_paths)
            if not isinstance(fields, list):
                fields = rule.source_paths
            parts: list[str] = []
            for field in fields:
                if not isinstance(field, str):
                    continue
                text = get_first_text(source_ir, field)
                if text:
                    parts.append(text)
            if parts and output_keys:
                for output_key in output_keys:
                    add_ir_value(target_ir, output_key, IRValue(text=sep.join(parts)))
                report.applied_rule_ids.append(rule.id)
            else:
                report.unmapped_fields.extend(rule.source_paths)
            continue

        if op == "value_map":
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
            if target_term and source_values:
                for value in source_values:
                    add_ir_value(target_ir, target_term, value)
                report.applied_rule_ids.append(rule.id)
            else:
                report.unmapped_fields.extend(rule.source_paths)
            continue

        if op == "split":
            source_values = _values_for_source_paths(source_ir, rule.source_paths)
            if not source_values or not output_keys:
                report.unmapped_fields.extend(rule.source_paths)
                continue
            chunks = [x.strip() for x in source_values[0].text.split(";") if x.strip()]
            for idx, chunk in enumerate(chunks):
                key = output_keys[min(idx, len(output_keys) - 1)]
                add_ir_value(target_ir, key, IRValue(text=chunk))
            report.applied_rule_ids.append(rule.id)
            continue

        source_values = _values_for_source_paths(source_ir, rule.source_paths)
        if source_values and output_keys:
            for key in output_keys:
                for value in source_values:
                    add_ir_value(target_ir, key, value)
            report.applied_rule_ids.append(rule.id)
        else:
            report.unmapped_fields.extend(rule.source_paths)

    report.unmapped_fields = sorted(set(report.unmapped_fields))
    return target_ir, report
