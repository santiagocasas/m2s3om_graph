from kaigraph.benchmark import benchmark_summary_to_csv, benchmark_summary_to_json
from kaigraph.benchmark.metrics import compare_ir_detailed
from kaigraph.benchmark.runner import BenchmarkCase, BenchmarkSummary
from kaigraph.transform import IRValue


def test_compare_ir_detailed_metrics() -> None:
    expected = {
        "dcterms:title": [IRValue(text="A title")],
        "dcterms:creator": [IRValue(text="Alice")],
    }
    actual = {
        "dcterms:title": [IRValue(text="A title")],
        "dcterms:creator": [IRValue(text="Alicia")],
    }
    metrics, diffs, confusion = compare_ir_detailed(
        actual, expected, semantic_loss_rules=1, total_rules=10
    )
    assert 0.0 <= metrics.field_coverage <= 1.0
    assert metrics.semantic_loss_rate == 0.1
    assert len(diffs) == 2
    assert "dcterms:creator" in confusion


def test_report_generation() -> None:
    metrics, diffs, confusion = compare_ir_detailed(
        {"dcterms:title": [IRValue(text="A")]},
        {"dcterms:title": [IRValue(text="A")]},
    )
    summary = BenchmarkSummary(
        cases=[
            BenchmarkCase(
                case_id="1",
                direction="datacite_to_dc",
                metrics=metrics,
                field_diffs=diffs,
                confusion_matrix=confusion,
            )
        ]
    )
    as_json = benchmark_summary_to_json(summary)
    as_csv = benchmark_summary_to_csv(summary)
    assert "aggregate" in as_json
    assert "case_id" in as_csv
