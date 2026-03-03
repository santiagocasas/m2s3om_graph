import csv
import io
import json

import streamlit as st

from state import get_store, sssom_dir
from kaigraph.candidates import suggest_candidate_mappings
from kaigraph.db import CrosswalkRecord, MappingType
from kaigraph.rdamsc import backfill_kg_from_sssom
from kaigraph.rdamsc import (
    ingest_rdamsc_crosswalk_docs,
    sssom_output_path,
    sync_rdamsc_catalog,
)
from kaigraph.rdamsc.pipeline import (
    load_pipeline_status,
    resolve_crosswalk_status,
    save_pipeline_status,
    status_label,
)
from kaigraph.sssom import load_sssom_rules


def _stats(rules_count: int, missing: int, conditional: int, aggregation: int) -> None:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rules", rules_count)
    c2.metric("Missing", missing)
    c3.metric("Conditional", conditional)
    c4.metric("Aggregation", aggregation)


def _rdamsc_crosswalks() -> list[CrosswalkRecord]:
    store = get_store()
    return [
        x
        for x in store.list_crosswalks()
        if x.msc_id is not None and x.msc_id.startswith("msc:")
    ]


def _status_code(
    crosswalk: CrosswalkRecord,
    status_map: dict[str, dict[str, object]],
) -> str:
    return resolve_crosswalk_status(get_store(), crosswalk, sssom_dir(), status_map)


def _remember_result(
    crosswalk: CrosswalkRecord,
    result: dict[str, object],
    status_map: dict[str, dict[str, object]],
) -> None:
    if bool(result.get("ok")):
        status = "ready"
    else:
        reason = str(result.get("reason", "unknown"))
        if reason == "artifacts_unreachable":
            status = "failed_unreachable"
        elif reason == "artifacts_unsupported":
            status = "failed_unsupported"
        else:
            status = "failed_parse"
    status_map[crosswalk.id] = {
        "crosswalk_id": crosswalk.id,
        "msc_id": crosswalk.msc_id,
        "name": crosswalk.name,
        "status": status,
        "label": status_label(status),
        "result": result,
    }
    _ = save_pipeline_status(status_map)


def _display_artifact_checks(result: dict[str, object]) -> None:
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
    crosswalk: CrosswalkRecord,
    status_map: dict[str, dict[str, object]],
    *,
    force: bool = False,
) -> dict[str, object]:
    code = _status_code(crosswalk, status_map)
    if code == "ready" and not force:
        return {"ok": True, "reason": "already_ready"}
    if code == "kg_out_of_sync" and not force:
        loaded = backfill_kg_from_sssom(get_store(), crosswalk, sssom_dir())
        result = {"ok": True, "reason": "kg_backfill", "backfilled_rules": loaded}
        _remember_result(crosswalk, result, status_map)
        return result

    result = ingest_rdamsc_crosswalk_docs(
        get_store(),
        crosswalk.id,
        sssom_dir(),
    )
    _remember_result(crosswalk, result, status_map)
    return result


def _ingest_all(
    status_map: dict[str, dict[str, object]],
    *,
    force: bool = False,
) -> None:
    crosswalks = _rdamsc_crosswalks()
    if not crosswalks:
        st.warning("No RDAMSC mappings available.")
        return

    ok = 0
    skipped = 0
    failed = 0
    for crosswalk in crosswalks:
        code = _status_code(crosswalk, status_map)
        if code == "ready" and not force:
            skipped += 1
            continue
        result = _ingest_selected(crosswalk, status_map, force=force)
        if bool(result.get("ok")):
            if result.get("reason") == "already_ready":
                skipped += 1
            else:
                ok += 1
        else:
            failed += 1
    st.success(f"Completed. Success: {ok}, skipped ready: {skipped}, failed: {failed}.")


def render() -> None:
    st.header("Crosswalk Browser")
    st.caption("Browse RDAMSC mappings, inspect rules, and export SSSOM/JSON/CSV.")
    st.markdown(
        "RDAMSC = RDA Metadata Standards Catalog. "
        "Website: [rdamsc.bath.ac.uk](https://rdamsc.bath.ac.uk/) | "
        "API docs: [SwaggerHub](https://app.swaggerhub.com/apis-docs/alex-ball/rda-metadata-standards-catalog/2.1.0)"
    )

    status_map = load_pipeline_status()
    crosswalks = _rdamsc_crosswalks()
    counts: dict[str, int] = {
        "ready": 0,
        "kg_out_of_sync": 0,
        "missing_sssom": 0,
        "failed_unreachable": 0,
        "failed_unsupported": 0,
        "failed_parse": 0,
    }
    for crosswalk in crosswalks:
        code = _status_code(crosswalk, status_map)
        if code not in counts:
            counts["failed_parse"] += 1
        else:
            counts[code] += 1

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

    if st.button("Refresh RDAMSC catalog (optional)", key="crosswalk_sync_optional"):
        try:
            count = sync_rdamsc_catalog(get_store())
            st.success(f"Catalog refreshed. Synced {count} mappings.")
            crosswalks = _rdamsc_crosswalks()
        except Exception as exc:
            st.error(f"Catalog sync failed: {exc}")

    with st.expander("Maintenance (optional)", expanded=False):
        st.caption(
            "Artifacts are converted to markdown via MarkItDown first. "
            "Use these actions only if you want to regenerate artifacts and rules."
        )
        c1, c2 = st.columns(2)
        if c1.button(
            "Generate missing SSSOM for all", key="crosswalk_ingest_missing_all"
        ):
            _ingest_all(status_map, force=False)
            status_map = load_pipeline_status()
        if c2.button(
            "Force re-ingest all supported docs", key="crosswalk_ingest_force_all"
        ):
            _ingest_all(status_map, force=True)
            status_map = load_pipeline_status()

    if not crosswalks:
        st.warning(
            "No RDAMSC mappings in store. Use the optional refresh button above."
        )
        return

    show_non_ready_only = st.checkbox(
        "Show only mappings not ready",
        value=False,
        key="crosswalk_show_missing_only",
    )
    if show_non_ready_only:
        crosswalks = [
            x for x in crosswalks if _status_code(x, status_map) not in {"ready"}
        ]
        if not crosswalks:
            st.info("All RDAMSC mappings are ready.")
            return

    selected = st.selectbox(
        "Crosswalk",
        crosswalks,
        format_func=lambda x: f"{x.name} ({x.msc_id}) [{status_label(_status_code(x, status_map))}]",
        key="crosswalk_browser_select",
    )

    c1, c2 = st.columns(2)
    if c1.button("Generate SSSOM for selected", key="crosswalk_generate_selected"):
        try:
            result = _ingest_selected(selected, status_map, force=False)
            if result.get("reason") == "already_ready":
                st.info("Mapping already ready; no re-ingestion needed.")
            elif result.get("reason") == "kg_backfill":
                st.success(
                    f"Loaded {result.get('backfilled_rules', 0)} rules from SSSOM into KG."
                )
            elif bool(result.get("ok")):
                st.success(
                    f"Generated {result.get('inserted_rules', 0)} new rules "
                    f"(total {result.get('total_rules', 0)}) and wrote {result.get('sssom_path')}"
                )
            else:
                st.warning(f"Ingestion failed: {result.get('reason')}")
                _display_artifact_checks(result)
            status_map = load_pipeline_status()
        except Exception as exc:
            st.error(f"Generation failed: {exc}")
    if c2.button("Force re-ingest selected (advanced)", key="crosswalk_force_selected"):
        try:
            result = _ingest_selected(selected, status_map, force=True)
            if bool(result.get("ok")):
                st.success(
                    f"Re-ingested mapping; total rules now {result.get('total_rules', 0)}"
                )
            else:
                st.warning(f"Re-ingestion failed: {result.get('reason')}")
                _display_artifact_checks(result)
            status_map = load_pipeline_status()
        except Exception as exc:
            st.error(f"Re-ingestion failed: {exc}")

    bundle = get_store().get_crosswalk_bundle(selected.id)
    if bundle is None:
        st.error("Crosswalk bundle not found")
        return

    sssom_path = sssom_output_path(sssom_dir(), selected.id)
    sssom_rules = (
        load_sssom_rules(sssom_path, selected.id) if sssom_path.exists() else []
    )
    rules = bundle.rules if bundle.rules else sssom_rules
    if not bundle.rules and sssom_rules:
        st.info(
            "KG has no rules for this mapping yet. Showing authoritative SSSOM rules."
        )

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
    st.write(f"Pipeline status: `{status_label(_status_code(selected, status_map))}`")
    if sssom_path.exists():
        st.write(f"SSSOM file: `{sssom_path}`")
    else:
        st.write(f"SSSOM file: not generated yet (`{sssom_path}`)")
    _stats(len(rules), missing_rules, conditional, aggregation)
    st.caption(f"Estimated loss rate: {loss_rate:.1f}%")

    last = status_map.get(selected.id, {})
    last_result = last.get("result")
    if isinstance(last_result, dict) and not bool(last_result.get("ok", True)):
        st.warning(f"Last ingestion failure reason: {last_result.get('reason')}")
        _display_artifact_checks(last_result)

    st.subheader("Rules")
    if not rules:
        st.info(
            "No rules extracted yet for this mapping. "
            "The source documentation may require parser improvements or assisted curation."
        )
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

    max_rows = st.number_input(
        "Max rules to show",
        min_value=10,
        max_value=500,
        value=120,
        step=10,
    )
    filtered = filtered[: int(max_rows)]

    st.write(f"Showing {len(filtered)} of {len(rules)} rules")
    for rule in filtered:
        source_row = rule.source_paths[0] if rule.source_paths else "n/a"
        source_label = (
            rule.source_paths[1] if len(rule.source_paths) > 1 else source_row
        )
        title = (
            f"{source_row} ({source_label}) -> "
            f"{', '.join(rule.target_paths) if rule.target_paths else 'n/a'} "
            f"[{rule.mapping_type.value}]"
        )
        with st.expander(title):
            st.write(f"Source field: {source_label}")
            st.write(f"Confidence: {rule.confidence:.2f}")
            st.write(
                f"Ambiguity: {rule.ambiguity} | Semantic loss: {rule.semantic_loss}"
            )
            st.code(json.dumps(rule.transform, indent=2), language="json")
            if rule.notes:
                st.caption(rule.notes)
            for evidence in rule.evidence:
                st.markdown(
                    f"- Source **{evidence.source}**, row **{evidence.row_id}**: {evidence.snippet}"
                )

            if st.button("Suggest AI candidate mappings", key=f"suggest_{rule.id}"):
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
                st.caption(
                    "Candidate suggestions are non-authoritative and never overwrite baseline rules."
                )
                for item in suggestions:
                    st.write(
                        f"- {item.target_path} (confidence {item.confidence:.2f}) - {item.rationale}"
                    )

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
