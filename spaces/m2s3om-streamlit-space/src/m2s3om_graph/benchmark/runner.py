from dataclasses import dataclass, field

from m2s3om_graph.db import CrosswalkBundle
from m2s3om_graph.interop.elib import (
    elib_export_urls,
    fetch_export,
    parse_dc_export_text_to_ir,
    parse_openaire_xml_to_ir,
)
from m2s3om_graph.transform.apply import apply_mapping_rules

from .metrics import ComparisonMetrics, FieldDiff, compare_ir_detailed


@dataclass
class BenchmarkCase:
    case_id: str
    direction: str
    metrics: ComparisonMetrics
    field_diffs: list[FieldDiff]
    confusion_matrix: dict[str, dict[str, int]]
    unmapped_fields: list[str] = field(default_factory=list)


@dataclass
class BenchmarkSummary:
    cases: list[BenchmarkCase]

    @property
    def avg_field_coverage(self) -> float:
        if not self.cases:
            return 0.0
        return sum(x.metrics.field_coverage for x in self.cases) / len(self.cases)

    @property
    def avg_value_overlap(self) -> float:
        if not self.cases:
            return 0.0
        return sum(x.metrics.value_overlap for x in self.cases) / len(self.cases)

    @property
    def avg_semantic_loss_rate(self) -> float:
        if not self.cases:
            return 0.0
        return sum(x.metrics.semantic_loss_rate for x in self.cases) / len(self.cases)


def run_fixture_benchmark(
    crosswalk: CrosswalkBundle,
    source_xml: str,
    expected_target_xml: str,
    n_cases: int,
) -> BenchmarkSummary:
    source_ir = parse_openaire_xml_to_ir(source_xml)
    expected_ir = parse_dc_export_text_to_ir(expected_target_xml)

    cases: list[BenchmarkCase] = []
    for idx in range(max(1, n_cases)):
        actual_ir, report = apply_mapping_rules(source_ir, crosswalk.rules)
        metrics, diffs, confusion = compare_ir_detailed(
            actual_ir,
            expected_ir,
            semantic_loss_rules=len(report.semantic_loss_rules),
            total_rules=len(crosswalk.rules),
        )
        cases.append(
            BenchmarkCase(
                case_id=f"fixture-{idx + 1}",
                direction="datacite_to_dc",
                metrics=metrics,
                field_diffs=diffs,
                confusion_matrix=confusion,
                unmapped_fields=report.unmapped_fields,
            )
        )
    return BenchmarkSummary(cases=cases)


def run_elib_benchmark(
    crosswalk: CrosswalkBundle,
    record_ids: list[str],
) -> BenchmarkSummary:
    cases: list[BenchmarkCase] = []
    for rid in record_ids:
        urls = elib_export_urls(rid)
        openaire_xml = fetch_export(urls["openaire"])
        dc_text = fetch_export(urls["dublin_core"])

        source_ir = parse_openaire_xml_to_ir(openaire_xml)
        expected_ir = parse_dc_export_text_to_ir(dc_text)
        actual_ir, report = apply_mapping_rules(source_ir, crosswalk.rules)
        metrics, diffs, confusion = compare_ir_detailed(
            actual_ir,
            expected_ir,
            semantic_loss_rules=len(report.semantic_loss_rules),
            total_rules=len(crosswalk.rules),
        )
        cases.append(
            BenchmarkCase(
                case_id=rid,
                direction="datacite_to_dc",
                metrics=metrics,
                field_diffs=diffs,
                confusion_matrix=confusion,
                unmapped_fields=report.unmapped_fields,
            )
        )
    return BenchmarkSummary(cases=cases)
