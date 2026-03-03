from dataclasses import dataclass
import re

from kaigraph.transform import IRRecord


def _normalize(text: str) -> str:
    compact = " ".join(text.lower().split())
    return re.sub(r"[^a-z0-9:/._ -]", "", compact)


@dataclass
class FieldDiff:
    field: str
    expected_values: list[str]
    actual_values: list[str]
    matched_values: list[str]
    missing_values: list[str]
    extra_values: list[str]
    normalized_overlap: float
    tp: int
    fp: int
    fn: int


@dataclass
class ComparisonMetrics:
    field_coverage: float
    value_overlap: float
    normalized_difference_rate: float
    semantic_loss_rate: float
    missing_field_count: int
    mismatched_field_count: int


def compare_ir_detailed(
    actual: IRRecord,
    expected: IRRecord,
    semantic_loss_rules: int = 0,
    total_rules: int = 0,
) -> tuple[ComparisonMetrics, list[FieldDiff], dict[str, dict[str, int]]]:
    expected_fields = set(expected)
    actual_fields = set(actual)
    all_fields = sorted(expected_fields | actual_fields)

    coverage = (
        len(expected_fields & actual_fields) / len(expected_fields)
        if expected_fields
        else 1.0
    )
    field_diffs: list[FieldDiff] = []
    overlaps: list[float] = []
    missing_field_count = 0
    mismatched_field_count = 0
    confusion: dict[str, dict[str, int]] = {}

    for field in all_fields:
        exp_vals = [
            _normalize(v.text) for v in expected.get(field, []) if v.text.strip()
        ]
        act_vals = [_normalize(v.text) for v in actual.get(field, []) if v.text.strip()]
        exp_set = set(exp_vals)
        act_set = set(act_vals)
        matched = sorted(exp_set & act_set)
        missing = sorted(exp_set - act_set)
        extra = sorted(act_set - exp_set)

        if field in expected_fields and field not in actual_fields:
            missing_field_count += 1
        if missing or extra:
            mismatched_field_count += 1

        overlap = (
            len(matched) / len(exp_set) if exp_set else (1.0 if not act_set else 0.0)
        )
        overlaps.append(overlap)
        tp = len(matched)
        fp = len(extra)
        fn = len(missing)
        confusion[field] = {"tp": tp, "fp": fp, "fn": fn}

        field_diffs.append(
            FieldDiff(
                field=field,
                expected_values=sorted(exp_set),
                actual_values=sorted(act_set),
                matched_values=matched,
                missing_values=missing,
                extra_values=extra,
                normalized_overlap=overlap,
                tp=tp,
                fp=fp,
                fn=fn,
            )
        )

    value_overlap = sum(overlaps) / len(overlaps) if overlaps else 1.0
    norm_diff_rate = 1.0 - value_overlap
    semantic_loss_rate = semantic_loss_rules / total_rules if total_rules else 0.0

    metrics = ComparisonMetrics(
        field_coverage=coverage,
        value_overlap=value_overlap,
        normalized_difference_rate=norm_diff_rate,
        semantic_loss_rate=semantic_loss_rate,
        missing_field_count=missing_field_count,
        mismatched_field_count=mismatched_field_count,
    )
    return metrics, field_diffs, confusion


def compare_ir(
    actual: IRRecord, expected: IRRecord
) -> tuple[float, float, list[FieldDiff]]:
    metrics, field_diffs, _ = compare_ir_detailed(actual, expected)
    return metrics.field_coverage, metrics.value_overlap, field_diffs
