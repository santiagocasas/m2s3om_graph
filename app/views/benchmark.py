import streamlit as st

from state import get_store
from kaigraph.benchmark import (
    benchmark_summary_to_csv,
    benchmark_summary_to_json,
    run_elib_benchmark,
)


def render() -> None:
    st.header("Benchmark")
    st.caption("Batch benchmark against eLib OpenAIRE and DC exports.")
    store = get_store()
    crosswalks = [
        x for x in store.list_crosswalks() if x.msc_id and x.msc_id.startswith("msc:")
    ]
    if not crosswalks:
        st.warning("No RDAMSC crosswalks available.")
        return

    selected = st.selectbox(
        "Crosswalk",
        crosswalks,
        format_func=lambda x: f"{x.name} ({x.id})",
        key="benchmark_crosswalk_select",
    )
    ids_input = st.text_area(
        "Record IDs (one per line)",
        value="204960\n19460",
        help="Use eLib numeric IDs.",
    )
    raw_ids = [line.strip() for line in ids_input.splitlines() if line.strip()]
    ids: list[str] = []
    invalid: list[str] = []
    for item in raw_ids:
        if item.isdigit() and item not in ids:
            ids.append(item)
        else:
            invalid.append(item)

    if invalid:
        st.warning(f"Ignored invalid IDs: {', '.join(invalid)}")

    if not ids:
        st.info("Add at least one valid numeric eLib record ID to run the benchmark.")
        return

    st.caption(f"Valid IDs loaded: {len(ids)}")
    n_records = st.number_input(
        "How many IDs to benchmark",
        min_value=1,
        max_value=len(ids),
        value=min(2, len(ids)),
        step=1,
    )

    if st.button("Run benchmark", type="primary"):
        bundle = store.get_crosswalk_bundle(selected.id)
        if bundle is None:
            st.error("Crosswalk bundle missing")
            return
        selected_ids = ids[: int(n_records)]
        try:
            summary = run_elib_benchmark(bundle, selected_ids)
        except Exception as exc:
            st.error(f"Benchmark failed: {exc}")
            return

        c1, c2, c3 = st.columns(3)
        c1.metric("Avg field coverage", f"{summary.avg_field_coverage:.2f}")
        c2.metric("Avg value overlap", f"{summary.avg_value_overlap:.2f}")
        c3.metric("Avg semantic loss", f"{summary.avg_semantic_loss_rate:.2f}")

        st.subheader("Per-record overview")
        st.table(
            [
                {
                    "record_id": case.case_id,
                    "coverage": round(case.metrics.field_coverage, 3),
                    "value_overlap": round(case.metrics.value_overlap, 3),
                    "missing_fields": case.metrics.missing_field_count,
                    "mismatched_fields": case.metrics.mismatched_field_count,
                }
                for case in summary.cases
            ]
        )

        worst = sorted(
            summary.cases,
            key=lambda case: (
                case.metrics.field_coverage,
                case.metrics.value_overlap,
            ),
        )[:5]
        st.subheader("Worst cases")
        for case in worst:
            st.write(
                f"- {case.case_id}: coverage={case.metrics.field_coverage:.2f}, overlap={case.metrics.value_overlap:.2f}, mismatched={case.metrics.mismatched_field_count}"
            )

        st.subheader("Per-case confusion matrix (field totals)")
        for case in summary.cases:
            total_tp = sum(v["tp"] for v in case.confusion_matrix.values())
            total_fp = sum(v["fp"] for v in case.confusion_matrix.values())
            total_fn = sum(v["fn"] for v in case.confusion_matrix.values())
            st.write(f"{case.case_id}: TP={total_tp}, FP={total_fp}, FN={total_fn}")

        csv_report = benchmark_summary_to_csv(summary)
        json_report = benchmark_summary_to_json(summary)
        d1, d2 = st.columns(2)
        d1.download_button(
            "Download benchmark CSV", csv_report, file_name="benchmark_report.csv"
        )
        d2.download_button(
            "Download benchmark JSON", json_report, file_name="benchmark_report.json"
        )
