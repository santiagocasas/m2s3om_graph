from pathlib import Path

import streamlit as st

from state import ensure_store, sssom_dir
from kaigraph.rdamsc.contracts import PipelineStatusMap
from kaigraph.rdamsc.pipeline import (
    load_pipeline_status,
    resolve_crosswalk_status,
    run_bootstrap_pipeline,
    status_label,
)


def _status_rows() -> list[dict[str, object]]:
    store = ensure_store()
    status_map: PipelineStatusMap = load_pipeline_status()
    rows: list[dict[str, object]] = []
    for crosswalk in store.list_crosswalks():
        if not crosswalk.msc_id or not crosswalk.msc_id.startswith("msc:"):
            continue
        status = resolve_crosswalk_status(store, crosswalk, sssom_dir(), status_map)
        last = status_map.get(crosswalk.id, {})
        result = last.get("result")
        reason = ""
        if isinstance(result, dict):
            value = result.get("reason")
            reason = str(value) if value is not None else ""
        rows.append(
            {
                "msc_id": crosswalk.msc_id,
                "name": crosswalk.name,
                "status": status_label(status),
                "reason": reason,
                "updated_at": last.get("updated_at", ""),
            }
        )
    rows.sort(key=lambda x: str(x["msc_id"]))
    return rows


def _ensure_pipeline_session_state() -> None:
    if "pipeline_logs" not in st.session_state:
        st.session_state["pipeline_logs"] = []
    if "pipeline_last_result" not in st.session_state:
        st.session_state["pipeline_last_result"] = None


def _append_pipeline_log(log_box, line: str) -> None:
    logs = st.session_state["pipeline_logs"]
    logs.append(line)
    if len(logs) > 2000:
        logs[:] = logs[-2000:]
    log_box.code("\n".join(logs[-300:]), language="text")


def _run_pipeline_action(
    store,
    log_box,
    *,
    selected,
    force: bool,
    selected_only: bool,
    start_message: str,
    end_message: str,
) -> None:
    if selected_only and selected is None:
        st.warning("No mapping available")
        return

    st.session_state["pipeline_logs"] = []
    _append_pipeline_log(log_box, start_message)
    result = run_bootstrap_pipeline(
        store,
        sssom_dir(),
        force=force,
        only_crosswalk_id=selected.id
        if selected_only and selected is not None
        else None,
        logger=lambda line: _append_pipeline_log(log_box, line),
    )
    st.session_state["pipeline_last_result"] = result
    _append_pipeline_log(log_box, end_message)


def _render_pipeline_controls(store, selected, log_box) -> None:
    c1, c2, c3 = st.columns(3)
    if c1.button("Run full pipeline", key="pipeline_run_full", type="primary"):
        _run_pipeline_action(
            store,
            log_box,
            selected=selected,
            force=False,
            selected_only=False,
            start_message="[ui] Running full pipeline",
            end_message="[ui] Pipeline finished",
        )

    if c2.button("Run selected mapping", key="pipeline_run_selected"):
        selected_msc_id = selected.msc_id if selected is not None else "n/a"
        _run_pipeline_action(
            store,
            log_box,
            selected=selected,
            force=False,
            selected_only=True,
            start_message=f"[ui] Running pipeline for {selected_msc_id}",
            end_message="[ui] Selected mapping pipeline finished",
        )

    if c3.button("Force re-run selected", key="pipeline_force_selected"):
        selected_msc_id = selected.msc_id if selected is not None else "n/a"
        _run_pipeline_action(
            store,
            log_box,
            selected=selected,
            force=True,
            selected_only=True,
            start_message=f"[ui] Force pipeline run for {selected_msc_id}",
            end_message="[ui] Forced pipeline finished",
        )


def _render_pipeline_logs(log_box) -> None:
    logs = st.session_state["pipeline_logs"]
    if logs:
        log_box.code("\n".join(logs[-300:]), language="text")
        return
    st.code("No pipeline run in this session yet.", language="text")


def _render_last_pipeline_result() -> None:
    last_result = st.session_state.get("pipeline_last_result")
    if isinstance(last_result, dict):
        st.subheader("Last pipeline result")
        st.json(last_result)


def _render_mapping_status_table() -> None:
    st.subheader("Mapping pipeline status")
    rows = _status_rows()
    if rows:
        st.dataframe(rows, use_container_width=True, hide_index=True)
        return
    st.info("No RDAMSC mappings loaded yet.")


def _render_status_file_and_bootstrap_log() -> None:
    status_file = Path(".local/rdamsc_pipeline_status.json")
    st.caption(f"Status file: `{status_file.resolve()}`")

    st.subheader("Startup bootstrap log")
    bootstrap_log = Path(".local/bootstrap_rdamsc.log")
    if bootstrap_log.exists():
        st.code(bootstrap_log.read_text(encoding="utf-8")[-12000:], language="text")
        return
    st.caption("No startup bootstrap log found yet.")


def render() -> None:
    st.header("Pipeline")
    st.caption(
        "Run the full RDAMSC ingestion pipeline with step-by-step logs, then inspect per-mapping status."
    )
    st.caption(
        "Stages: sync catalog -> inspect artifacts -> ingest docs -> load KG -> write SSSOM"
    )

    _ensure_pipeline_session_state()

    store = ensure_store()
    msc_crosswalks = [
        x
        for x in store.list_crosswalks()
        if x.msc_id is not None and x.msc_id.startswith("msc:")
    ]

    selected = None
    if msc_crosswalks:
        selected = st.selectbox(
            "Mapping (for single-run)",
            msc_crosswalks,
            format_func=lambda x: f"{x.name} ({x.msc_id})",
            key="pipeline_selected_crosswalk",
        )

    log_box = st.empty()
    _render_pipeline_controls(store, selected, log_box)
    _render_pipeline_logs(log_box)
    _render_last_pipeline_result()
    _render_mapping_status_table()
    _render_status_file_and_bootstrap_log()
