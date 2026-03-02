import csv
import io
import json

from .runner import BenchmarkSummary


def benchmark_summary_to_json(summary: BenchmarkSummary) -> str:
    payload = {
        "aggregate": {
            "avg_field_coverage": summary.avg_field_coverage,
            "avg_value_overlap": summary.avg_value_overlap,
            "avg_semantic_loss_rate": summary.avg_semantic_loss_rate,
            "cases": len(summary.cases),
        },
        "cases": [
            {
                "case_id": case.case_id,
                "direction": case.direction,
                "metrics": {
                    "field_coverage": case.metrics.field_coverage,
                    "value_overlap": case.metrics.value_overlap,
                    "normalized_difference_rate": case.metrics.normalized_difference_rate,
                    "semantic_loss_rate": case.metrics.semantic_loss_rate,
                    "missing_field_count": case.metrics.missing_field_count,
                    "mismatched_field_count": case.metrics.mismatched_field_count,
                },
                "unmapped_fields": case.unmapped_fields,
                "field_diffs": [
                    {
                        "field": diff.field,
                        "missing_values": diff.missing_values,
                        "extra_values": diff.extra_values,
                        "overlap": diff.normalized_overlap,
                    }
                    for diff in case.field_diffs
                ],
                "confusion_matrix": case.confusion_matrix,
            }
            for case in summary.cases
        ],
    }
    return json.dumps(payload, indent=2)


def benchmark_summary_to_csv(summary: BenchmarkSummary) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "case_id",
            "direction",
            "field_coverage",
            "value_overlap",
            "normalized_difference_rate",
            "semantic_loss_rate",
            "missing_field_count",
            "mismatched_field_count",
            "unmapped_fields",
        ]
    )
    for case in summary.cases:
        writer.writerow(
            [
                case.case_id,
                case.direction,
                f"{case.metrics.field_coverage:.4f}",
                f"{case.metrics.value_overlap:.4f}",
                f"{case.metrics.normalized_difference_rate:.4f}",
                f"{case.metrics.semantic_loss_rate:.4f}",
                case.metrics.missing_field_count,
                case.metrics.mismatched_field_count,
                ";".join(case.unmapped_fields),
            ]
        )
    return buffer.getvalue()
