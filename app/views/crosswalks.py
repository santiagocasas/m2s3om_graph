import csv
import io
import json
from pathlib import Path

import streamlit as st

from state import ensure_store, sssom_dir
from kaigraph.candidates.blablador import (
    last_suggestion_error,
    suggest_candidate_mappings,
)
from kaigraph.db import (
    CrosswalkBundle,
    CrosswalkRecord,
    CrosswalkStore,
    MappingRuleRecord,
    MappingType,
)
from kaigraph.rdamsc.ingest import (
    sssom_output_path,
    sync_rdamsc_catalog,
)
from kaigraph.rdamsc.contracts import PipelineResult, PipelineStatusMap, result_is_ok
from kaigraph.rdamsc.pipeline import (
    load_pipeline_status,
    resolve_crosswalk_status,
    run_bootstrap_pipeline,
    status_label,
)
from kaigraph.sssom import load_sssom_rules


def _stats(rules_count: int, missing: int, conditional: int, aggregation: int) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rules", rules_count)
    c2.metric("Missing", missing)
    c3.metric("Conditional", conditional)
    c4.metric("Aggregation", aggregation)


def _rdamsc_crosswalks(store: CrosswalkStore) -> list[CrosswalkRecord]:
    return [
        x
        for x in store.list_crosswalks()
        if x.msc_id is not None and x.msc_id.startswith("msc:")
    ]


def _status_code(
    store: CrosswalkStore,
    out_dir: Path,
    crosswalk: CrosswalkRecord,
    status_map: PipelineStatusMap,
) -> str:
    return resolve_crosswalk_status(store, crosswalk, out_dir, status_map)


def _display_artifact_checks(result: PipelineResult) -> None:
    checks = result.get("artifact_checks")
    if not isinstance(checks, list) or not checks:
        return

    status_labels = {
        "fetched": "Fetched",
        "fetch_error": "Unreachable",
        "conversion_error": "Conversion failed",
        "unsupported": "Unsupported",
    }

    rows: list[dict[str, object]] = []
    for item in checks:
        if not isinstance(item, dict):
            continue
        raw_status = str(item.get("status", ""))
        error = item.get("error")
        details = ""
        if error is not None:
            details = str(error)
            if len(details) > 200:
                details = details[:200] + "..."
        rows.append(
            {
                "URL": str(item.get("url", "")),
                "Extension": str(item.get("extension", "")),
                "Type": str(item.get("location_type", "")),
                "Status": status_labels.get(raw_status, raw_status or "Unknown"),
                "Details": details,
            }
        )

    if not rows:
        return

    st.caption("Artifact checks")
    st.dataframe(rows, use_container_width=True, hide_index=True)


def _ingest_selected(
    store: CrosswalkStore,
    out_dir: Path,
    crosswalk: CrosswalkRecord,
    *,
    force: bool = False,
) -> PipelineResult:
    pipeline_result = run_bootstrap_pipeline(
        store,
        out_dir,
        force=force,
        only_crosswalk_id=crosswalk.id,
    )
    processed = pipeline_result.get("processed", [])
    if not processed:
        return {
            "ok": False,
            "reason": "not_processed",
            "crosswalk_id": crosswalk.id,
        }
    first = processed[0]
    result = first.get("result")
    if isinstance(result, dict):
        return result
    return {
        "ok": False,
        "reason": "invalid_pipeline_result",
        "crosswalk_id": crosswalk.id,
    }


def _ingest_all(
    store: CrosswalkStore,
    out_dir: Path,
    *,
    force: bool = False,
) -> None:
    crosswalks = _rdamsc_crosswalks(store)
    if not crosswalks:
        st.warning("No RDAMSC mappings available.")
        return

    ok = 0
    skipped = 0
    failed = 0
    pipeline_result = run_bootstrap_pipeline(store, out_dir, force=force)
    processed = pipeline_result.get("processed", [])
    for item in processed:
        result = item.get("result")
        if not isinstance(result, dict):
            failed += 1
            continue
        if result_is_ok(result):
            if result.get("step") == "skipped_ready":
                skipped += 1
            else:
                ok += 1
        else:
            failed += 1
    st.success(f"Completed. Success: {ok}, skipped ready: {skipped}, failed: {failed}.")


def _render_intro() -> None:
    st.header("Crosswalk Browser")
    st.caption("Browse RDAMSC mappings, inspect rules, and export SSSOM/JSON/CSV.")
    st.markdown(
        "RDAMSC = RDA Metadata Standards Catalog. "
        "Website: [rdamsc.bath.ac.uk](https://rdamsc.bath.ac.uk/) | "
        "API docs: [SwaggerHub](https://app.swaggerhub.com/apis-docs/alex-ball/rda-metadata-standards-catalog/2.1.0)"
    )
    st.info(
        "Start here: 1) Select a mapping, 2) Generate SSSOM for selected, "
        "3) Inspect rules and evidence, 4) Export TSV/JSON/CSV."
    )


def _status_counts(
    store: CrosswalkStore,
    out_dir: Path,
    crosswalks: list[CrosswalkRecord],
    status_map: PipelineStatusMap,
) -> dict[str, int]:
    counts: dict[str, int] = {
        "ready": 0,
        "kg_out_of_sync": 0,
        "missing_sssom": 0,
        "failed_unreachable": 0,
        "failed_unsupported": 0,
        "failed_parse": 0,
    }
    for crosswalk in crosswalks:
        code = _status_code(store, out_dir, crosswalk, status_map)
        if code not in counts:
            counts["failed_parse"] += 1
            continue
        counts[code] += 1
    return counts


def _render_catalog_overview(
    store: CrosswalkStore,
    out_dir: Path,
    crosswalks: list[CrosswalkRecord],
    status_map: PipelineStatusMap,
) -> None:
    counts = _status_counts(store, out_dir, crosswalks, status_map)
    st.caption(
        " | ".join(
            [
                f"Catalog loaded: {len(crosswalks)}",
                f"Ready: {counts['ready']}",
                f"KG out of sync: {counts['kg_out_of_sync']}",
                f"Missing SSSOM: {counts['missing_sssom']}",
                f"Unreachable docs: {counts['failed_unreachable']}",
                f"Unsupported docs: {counts['failed_unsupported']}",
                f"Parse/extract failed: {counts['failed_parse']}",
            ]
        )
    )


def _render_maintenance_actions(
    store: CrosswalkStore,
    out_dir: Path,
) -> list[CrosswalkRecord]:
    crosswalks = _rdamsc_crosswalks(store)
    with st.expander("Maintenance (optional)", expanded=False):
        st.caption(
            "Artifacts are converted to markdown via MarkItDown first. "
            "Use these actions only if you want to regenerate artifacts and rules."
        )
        if st.button("Refresh RDAMSC catalog", key="crosswalk_sync_optional"):
            try:
                count = sync_rdamsc_catalog(store)
                st.success(f"Catalog refreshed. Synced {count} mappings.")
                crosswalks = _rdamsc_crosswalks(store)
            except Exception as exc:
                st.error(f"Catalog sync failed: {exc}")

        c1, c2 = st.columns(2)
        if c1.button(
            "Generate missing SSSOM for all", key="crosswalk_ingest_missing_all"
        ):
            _ingest_all(store, out_dir, force=False)
        if c2.button(
            "Force re-ingest all supported docs", key="crosswalk_ingest_force_all"
        ):
            _ingest_all(store, out_dir, force=True)

    return crosswalks


def _resolve_bundle_rules(
    store: CrosswalkStore,
    out_dir: Path,
    selected: CrosswalkRecord,
) -> tuple[CrosswalkBundle, Path, list[MappingRuleRecord]]:
    bundle = store.get_crosswalk_bundle(selected.id)
    if bundle is None:
        raise RuntimeError("Crosswalk bundle not found")
    sssom_path = sssom_output_path(out_dir, selected.id)
    sssom_rules = (
        load_sssom_rules(sssom_path, selected.id) if sssom_path.exists() else []
    )
    rules = bundle.rules if bundle.rules else sssom_rules
    if not bundle.rules and sssom_rules:
        st.info(
            "KG has no rules for this mapping yet. Showing authoritative SSSOM rules."
        )
    return bundle, sssom_path, rules


def _render_selected_summary(
    store: CrosswalkStore,
    out_dir: Path,
    selected: CrosswalkRecord,
    status_map: PipelineStatusMap,
    bundle: CrosswalkBundle,
    sssom_path: Path,
    rules: list[MappingRuleRecord],
) -> None:
    missing_rules = sum(1 for r in rules if r.mapping_type == MappingType.MISSING)
    conditional = sum(1 for r in rules if r.mapping_type == MappingType.CONDITIONAL)
    aggregation = sum(1 for r in rules if r.mapping_type == MappingType.AGGREGATION)
    loss_rate = (missing_rules / len(rules)) * 100 if rules else 0

    st.subheader("Summary")
    st.write(
        f"Source: **{bundle.source_standard.name}** -> Target: **{bundle.target_standard.name}**"
    )
    st.write(f"MSC ID: `{bundle.crosswalk.msc_id or 'n/a'}`")
    st.write(f"DOI: `{bundle.crosswalk.doi or 'n/a'}`")
    st.write(f"Primary document URI: `{bundle.crosswalk.doc_uri or 'n/a'}`")
    st.write(
        f"Pipeline status: `{status_label(_status_code(store, out_dir, selected, status_map))}`"
    )
    if sssom_path.exists():
        st.write(f"SSSOM file: `{sssom_path}`")
    else:
        st.write(f"SSSOM file: not generated yet (`{sssom_path}`)")
    _stats(len(rules), missing_rules, conditional, aggregation)
    st.caption(f"Estimated loss rate: {loss_rate:.1f}%")

    last = status_map.get(selected.id, {})
    last_result = last.get("result")
    if isinstance(last_result, dict) and not result_is_ok(last_result):
        st.warning(f"Last ingestion failure reason: {last_result.get('reason')}")
        _display_artifact_checks(last_result)


def _rule_filter_inputs() -> tuple[str, str, int]:
    filter_type = st.selectbox(
        "Mapping type",
        ["all"] + [x.value for x in MappingType],
        index=0,
        key="crosswalk_browser_mapping_type",
    )
    query = (
        st.text_input(
            "Search source/target fields",
            value="",
            placeholder="e.g. creatorName, publicationYear, dcterms:issued",
        )
        .strip()
        .lower()
    )
    max_rows = int(
        st.number_input(
            "Max rules to show",
            min_value=10,
            max_value=500,
            value=120,
            step=10,
        )
    )
    return filter_type, query, max_rows


def _filter_rules(
    rules: list[MappingRuleRecord],
    *,
    filter_type: str,
    query: str,
    max_rows: int,
) -> list[MappingRuleRecord]:
    filtered = rules
    if filter_type != "all":
        filtered = [x for x in filtered if x.mapping_type.value == filter_type]
    if query:
        filtered = [
            x
            for x in filtered
            if query in " ".join(x.source_paths).lower()
            or query in " ".join(x.target_paths).lower()
        ]
    return filtered[:max_rows]


def _render_candidate_suggestions(
    rule: MappingRuleRecord,
    rules: list[MappingRuleRecord],
) -> None:
    all_target_paths = sorted(
        {
            path
            for other_rule in rules
            for path in other_rule.target_paths
            if path.startswith("dcterms:")
        }
    )
    source_text = " ".join(rule.source_paths)
    suggestions = suggest_candidate_mappings(source_text, all_target_paths)
    suggestion_error = last_suggestion_error()
    if isinstance(suggestion_error, dict):
        operation = str(suggestion_error.get("operation", "suggest_candidate_mappings"))
        message = str(suggestion_error.get("message", "unknown error"))
        st.caption(f"LLM fallback used: {operation} failed ({message}).")
    st.caption(
        "Candidate suggestions are non-authoritative and never overwrite baseline rules."
    )
    for item in suggestions:
        st.write(
            f"- {item.target_path} (confidence {item.confidence:.2f}) - {item.rationale}"
        )


def _render_rule_card(rule: MappingRuleRecord, rules: list[MappingRuleRecord]) -> None:
    source_row = rule.source_paths[0] if rule.source_paths else "n/a"
    source_label = rule.source_paths[1] if len(rule.source_paths) > 1 else source_row
    title = (
        f"{source_row} ({source_label}) -> "
        f"{', '.join(rule.target_paths) if rule.target_paths else 'n/a'} "
        f"[{rule.mapping_type.value}]"
    )
    with st.expander(title):
        st.write(f"Source field: {source_label}")
        st.write(f"Confidence: {rule.confidence:.2f}")
        st.write(f"Ambiguity: {rule.ambiguity} | Semantic loss: {rule.semantic_loss}")
        st.code(json.dumps(rule.transform, indent=2), language="json")
        if rule.notes:
            st.caption(rule.notes)
        for evidence in rule.evidence:
            st.markdown(
                f"- Source **{evidence.source}**, row **{evidence.row_id}**: {evidence.snippet}"
            )

        if st.button("Suggest AI candidate mappings", key=f"suggest_{rule.id}"):
            _render_candidate_suggestions(rule, rules)


def _render_rules_section(rules: list[MappingRuleRecord]) -> None:
    st.subheader("Rules")
    if not rules:
        st.info(
            "No rules extracted yet for this mapping. "
            "The source documentation may require parser improvements or assisted curation."
        )
    filter_type, query, max_rows = _rule_filter_inputs()
    filtered = _filter_rules(
        rules,
        filter_type=filter_type,
        query=query,
        max_rows=max_rows,
    )

    st.write(f"Showing {len(filtered)} of {len(rules)} rules")
    for rule in filtered:
        _render_rule_card(rule, rules)


def _render_exports(rules: list[MappingRuleRecord], sssom_path: Path) -> None:
    st.subheader("Export")
    st.caption(
        "SSSOM TSV is authoritative for conversion. JSON and CSV are convenience exports."
    )
    rules_json = json.dumps([x.model_dump(mode="json") for x in rules], indent=2)
    csv_buffer = io.StringIO()
    writer = csv.writer(csv_buffer)
    writer.writerow(
        [
            "rule_id",
            "source_paths",
            "target_paths",
            "mapping_type",
            "confidence",
            "semantic_loss",
            "ambiguity",
        ]
    )
    for rule in rules:
        writer.writerow(
            [
                rule.id,
                ";".join(rule.source_paths),
                ";".join(rule.target_paths),
                rule.mapping_type.value,
                rule.confidence,
                rule.semantic_loss,
                rule.ambiguity,
            ]
        )

    if sssom_path.exists():
        st.download_button(
            "Download SSSOM TSV",
            sssom_path.read_text(encoding="utf-8"),
            file_name=sssom_path.name,
        )
    st.download_button(
        "Download rules JSON", rules_json, file_name="mapping_rules.json"
    )
    st.download_button(
        "Download rules CSV",
        csv_buffer.getvalue(),
        file_name="mapping_rules.csv",
    )


def _report_selected_ingest_result(result: PipelineResult, *, force: bool) -> None:
    if result_is_ok(result):
        step = str(result.get("step", ""))
        if step == "kg_backfill":
            st.success(
                f"Loaded {result.get('backfilled_rules', 0)} rules from SSSOM into KG."
            )
            return
        if step == "skipped_ready" and not force:
            st.info("Mapping already ready; no re-ingestion needed.")
            return
        if force:
            st.success(
                f"Re-ingested mapping; total rules now {result.get('total_rules', 0)}"
            )
            return
        st.success(
            f"Generated {result.get('inserted_rules', 0)} new rules "
            f"(total {result.get('total_rules', 0)}) and wrote {result.get('sssom_path')}"
        )
        return

    failure_label = "Re-ingestion failed" if force else "Ingestion failed"
    st.warning(f"{failure_label}: {result.get('reason')}")
    _display_artifact_checks(result)


def _run_selected_ingest(
    store: CrosswalkStore,
    out_dir: Path,
    selected: CrosswalkRecord,
    status_map: PipelineStatusMap,
    *,
    force: bool,
) -> PipelineStatusMap:
    try:
        result = _ingest_selected(store, out_dir, selected, force=force)
    except Exception as exc:
        error_label = "Re-ingestion failed" if force else "Generation failed"
        st.error(f"{error_label}: {exc}")
        return status_map

    _report_selected_ingest_result(result, force=force)
    return load_pipeline_status()


def _filter_crosswalks_for_display(
    store: CrosswalkStore,
    out_dir: Path,
    crosswalks: list[CrosswalkRecord],
    status_map: PipelineStatusMap,
) -> list[CrosswalkRecord]:
    show_non_ready_only = st.checkbox(
        "Show only mappings not ready",
        value=False,
        key="crosswalk_show_missing_only",
    )
    if not show_non_ready_only:
        return crosswalks

    filtered = [
        x for x in crosswalks if _status_code(store, out_dir, x, status_map) != "ready"
    ]
    if not filtered:
        st.info("All RDAMSC mappings are ready.")
    return filtered


def render() -> None:
    _render_intro()

    store = ensure_store()
    out_dir = sssom_dir()
    status_map = load_pipeline_status()
    crosswalks = _rdamsc_crosswalks(store)
    _render_catalog_overview(store, out_dir, crosswalks, status_map)
    crosswalks = _render_maintenance_actions(store, out_dir)
    status_map = load_pipeline_status()

    if not crosswalks:
        st.warning(
            "No RDAMSC mappings in store. Use the optional refresh button above."
        )
        return

    crosswalks = _filter_crosswalks_for_display(store, out_dir, crosswalks, status_map)
    if not crosswalks:
        return

    selected = st.selectbox(
        "Crosswalk",
        crosswalks,
        format_func=lambda x: (
            f"{x.name} ({x.msc_id}) "
            f"[{status_label(_status_code(store, out_dir, x, status_map))}]"
        ),
        key="crosswalk_browser_select",
    )

    if st.button(
        "Generate SSSOM for selected",
        key="crosswalk_generate_selected",
        type="primary",
    ):
        status_map = _run_selected_ingest(
            store,
            out_dir,
            selected,
            status_map,
            force=False,
        )

    with st.expander("Selected mapping advanced actions", expanded=False):
        if st.button("Force re-ingest selected", key="crosswalk_force_selected"):
            status_map = _run_selected_ingest(
                store,
                out_dir,
                selected,
                status_map,
                force=True,
            )

    try:
        bundle, sssom_path, rules = _resolve_bundle_rules(store, out_dir, selected)
    except RuntimeError as exc:
        st.error(str(exc))
        return

    _render_selected_summary(
        store,
        out_dir,
        selected,
        status_map,
        bundle,
        sssom_path,
        rules,
    )
    _render_rules_section(rules)
    _render_exports(rules, sssom_path)
