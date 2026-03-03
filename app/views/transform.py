import json
from xml.dom import minidom

import streamlit as st

from state import (
    DEFAULT_OAI_BASE_URL,
    DEFAULT_OAI_IDENTIFIER,
    get_store,
    sssom_dir,
)
from kaigraph.benchmark.metrics import compare_ir
from kaigraph.crosswalk import derive_reverse_rules
from kaigraph.db import CrosswalkBundle
from kaigraph.interop import parse_dc_export_text_to_ir, parse_openaire_xml_to_ir
from kaigraph.oai import OAIClient, parse_metadata_prefixes
from kaigraph.rdamsc import ensure_sssom_for_bundle, sssom_output_path
from kaigraph.sssom import load_sssom_rules
from kaigraph.transform import (
    apply_mapping_rules,
    ir_to_datacite_xml,
    ir_to_dublin_core_xml,
    parse_datacite_xml_to_ir,
    parse_oai_dc_xml_to_ir,
)

FORMAT_OPTIONS = {
    "oai_dc_xml": "OAI Dublin Core XML",
    "datacite_xml": "DataCite XML",
    "openaire_xml": "OpenAIRE XML",
    "dc_export_text": "Dublin Core export text",
}


def _pretty_xml(xml_text: str) -> str:
    try:
        parsed = minidom.parseString(xml_text)
        return parsed.toprettyxml(indent="  ")
    except Exception:
        return xml_text


def _authoritative_rules(bundle: CrosswalkBundle) -> list:
    path = sssom_output_path(sssom_dir(), bundle.crosswalk.id)
    if not path.exists():
        _ = ensure_sssom_for_bundle(bundle, sssom_dir())
    rules = load_sssom_rules(path, bundle.crosswalk.id)
    if rules:
        return rules
    return bundle.rules


def _parse_payload(payload: str, payload_format: str):
    if payload_format == "oai_dc_xml":
        return parse_oai_dc_xml_to_ir(payload)
    if payload_format == "datacite_xml":
        return parse_datacite_xml_to_ir(payload)
    if payload_format == "openaire_xml":
        return parse_openaire_xml_to_ir(payload)
    if payload_format == "dc_export_text":
        return parse_dc_export_text_to_ir(payload)
    raise ValueError(f"Unsupported format: {payload_format}")


def _serialize_target(target_ir, target_format: str) -> str:
    if target_format == "oai_dc_xml":
        return ir_to_dublin_core_xml(target_ir)
    if target_format == "datacite_xml":
        return ir_to_datacite_xml(target_ir)
    raise ValueError(
        "No serializer available for selected target format. "
        "Choose OAI Dublin Core XML or DataCite XML."
    )


def _to_internal_format(metadata_prefix: str) -> str | None:
    value = metadata_prefix.strip().lower()
    if value == "oai_dc":
        return "oai_dc_xml"
    if "datacite" in value:
        return "datacite_xml"
    return None


def _render_report(converted_ir, report, expected_ir) -> None:
    c1, c2, c3 = st.columns(3)
    c1.metric("Applied rules", str(len(report.applied_rule_ids)))
    c2.metric("Unmapped fields", str(len(report.unmapped_fields)))
    c3.metric("Semantic loss rules", str(len(report.semantic_loss_rules)))

    if expected_ir is not None:
        coverage, overlap, metrics = compare_ir(converted_ir, expected_ir)
        m1, m2, m3 = st.columns(3)
        m1.metric("Field coverage", f"{coverage:.2f}")
        m2.metric("Value overlap", f"{overlap:.2f}")
        m3.metric("Compared fields", str(len(metrics)))

        with st.expander("Field-by-field diff", expanded=False):
            for item in metrics:
                st.write(
                    f"- {item.field}: expected={len(item.expected_values)}, "
                    f"actual={len(item.actual_values)}, overlap={item.normalized_overlap:.2f}, "
                    f"missing={len(item.missing_values)}, extra={len(item.extra_values)}"
                )

    with st.expander("Transformation details", expanded=False):
        st.json(
            {
                "applied_rules": report.applied_rule_ids,
                "unmapped_fields": report.unmapped_fields,
                "semantic_loss_rules": report.semantic_loss_rules,
                "ambiguous_rules": report.ambiguous_rules,
            }
        )


def render() -> None:
    st.header("Convert One Record")
    st.caption(
        "Single workspace: fetch or paste one record, convert with a selected crosswalk, "
        "and review comparison metrics in one place."
    )
    st.info(
        "Use OAI-PMH fetch when you have an endpoint + identifier and want automatic format discovery. "
        "Use manual paste when you already have record payloads."
    )

    store = get_store()
    crosswalks = [
        x for x in store.list_crosswalks() if x.msc_id and x.msc_id.startswith("msc:")
    ]
    if not crosswalks:
        st.warning("No RDAMSC crosswalks available.")
        return

    selected_crosswalk = st.selectbox(
        "Crosswalk",
        crosswalks,
        format_func=lambda x: f"{x.name} ({x.msc_id})",
        key="transform_crosswalk_select",
    )
    bundle = store.get_crosswalk_bundle(selected_crosswalk.id)
    if bundle is None:
        st.error("Crosswalk not found")
        return

    rules = _authoritative_rules(bundle)
    use_reverse = st.checkbox(
        "Use derived reverse mapping (best effort)",
        value=False,
        help="Enable this when converting in the opposite direction of the curated mapping.",
    )
    working_rules = (
        derive_reverse_rules(bundle.model_copy(update={"rules": rules}))
        if use_reverse
        else rules
    )

    source_mode = st.radio(
        "Record source",
        ["Fetch from OAI-PMH", "Paste manually"],
        horizontal=True,
    )

    source_payload = ""
    source_format = "oai_dc_xml"
    expected_payload = ""
    expected_format = "oai_dc_xml"

    if source_mode == "Fetch from OAI-PMH":
        base_url = st.text_input("OAI-PMH base URL", value=DEFAULT_OAI_BASE_URL)
        identifier = st.text_input("Identifier", value=DEFAULT_OAI_IDENTIFIER)

        if "transform_prefixes" not in st.session_state:
            st.session_state["transform_prefixes"] = ["oai_dc"]

        if st.button("Discover metadata formats", key="transform_discover_formats"):
            try:
                client = OAIClient(base_url)
                xml_text = client.list_metadata_formats(identifier)
                prefixes = parse_metadata_prefixes(xml_text)
                st.session_state["transform_prefixes"] = prefixes or ["oai_dc"]
                st.success(
                    f"Found {len(st.session_state['transform_prefixes'])} metadata formats."
                )
            except Exception as exc:
                st.error(f"Format discovery failed: {exc}")

        prefixes = st.session_state["transform_prefixes"]
        source_prefix = st.selectbox(
            "Source metadataPrefix",
            prefixes,
            key="transform_source_prefix",
        )
        target_prefix = st.selectbox(
            "Comparison metadataPrefix (optional)",
            ["none", *prefixes],
            index=0,
            key="transform_target_prefix",
            help="Fetch a second payload to compare against converted output.",
        )

        fetch_clicked = st.button(
            "Fetch payload(s)",
            key="transform_fetch_payloads",
        )
        if fetch_clicked:
            try:
                client = OAIClient(base_url)
                source_payload = client.get_record(identifier, source_prefix)
                st.session_state["transform_source_payload"] = source_payload
                st.session_state["transform_source_format"] = _to_internal_format(
                    source_prefix
                )
            except Exception as exc:
                st.error(f"Failed to fetch source payload: {exc}")
                return

            if target_prefix != "none":
                try:
                    expected_payload = client.get_record(identifier, target_prefix)
                    st.session_state["transform_expected_payload"] = expected_payload
                    st.session_state["transform_expected_format"] = _to_internal_format(
                        target_prefix
                    )
                except Exception as exc:
                    st.warning(f"Failed to fetch comparison payload: {exc}")
                    st.session_state["transform_expected_payload"] = ""
                    st.session_state["transform_expected_format"] = None
            else:
                st.session_state["transform_expected_payload"] = ""
                st.session_state["transform_expected_format"] = None

        source_payload = st.session_state.get("transform_source_payload", "")
        source_format = st.session_state.get("transform_source_format", "oai_dc_xml")
        expected_payload = st.session_state.get("transform_expected_payload", "")
        expected_format = st.session_state.get(
            "transform_expected_format", "oai_dc_xml"
        )

        if source_payload:
            st.success("Source payload loaded.")
        if expected_payload:
            st.success("Comparison payload loaded.")

    else:
        source_format = st.selectbox(
            "Source payload format",
            options=list(FORMAT_OPTIONS.keys()),
            format_func=lambda x: FORMAT_OPTIONS[x],
            key="transform_source_format_manual",
        )
        source_payload = st.text_area(
            "Source payload",
            value="",
            height=220,
            placeholder="Paste source XML or text here.",
        )

        expected_enabled = st.checkbox(
            "Include expected/comparison payload",
            value=False,
            key="transform_enable_expected_manual",
        )
        if expected_enabled:
            expected_format = st.selectbox(
                "Expected payload format",
                options=list(FORMAT_OPTIONS.keys()),
                format_func=lambda x: FORMAT_OPTIONS[x],
                key="transform_expected_format_manual",
            )
            expected_payload = st.text_area(
                "Expected payload",
                value="",
                height=220,
                placeholder="Paste target representation for comparison.",
            )

    target_format = st.selectbox(
        "Convert to",
        ["oai_dc_xml", "datacite_xml"],
        format_func=lambda x: FORMAT_OPTIONS[x],
        key="transform_target_format",
    )

    if not st.button("Convert and compare", type="primary"):
        return

    if not source_payload.strip():
        st.warning("Provide or fetch a source payload first.")
        return
    if source_format is None:
        st.error(
            "Selected source metadataPrefix is not supported for conversion yet. "
            "Use oai_dc or a DataCite-compatible prefix."
        )
        return

    try:
        source_ir = _parse_payload(source_payload, source_format)
    except Exception as exc:
        st.error(f"Failed to parse source payload: {exc}")
        return

    try:
        converted_ir, report = apply_mapping_rules(source_ir, working_rules)
        transformed_payload = _serialize_target(converted_ir, target_format)
    except Exception as exc:
        st.error(f"Conversion failed: {exc}")
        return

    expected_ir = None
    if expected_payload.strip():
        if expected_format is None:
            st.warning(
                "Comparison payload was fetched in an unsupported prefix and was skipped."
            )
        else:
            try:
                expected_ir = _parse_payload(expected_payload, expected_format)
            except Exception as exc:
                st.warning(f"Comparison payload could not be parsed: {exc}")

    st.subheader("Result")
    _render_report(converted_ir, report, expected_ir)

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Transformed payload**")
        if target_format in {"oai_dc_xml", "datacite_xml"}:
            st.code(_pretty_xml(transformed_payload), language="xml")
        else:
            st.code(transformed_payload, language="text")
        file_name = (
            "transformed_dublincore.xml"
            if target_format == "oai_dc_xml"
            else "transformed_datacite.xml"
        )
        st.download_button(
            "Download transformed payload",
            transformed_payload,
            file_name=file_name,
        )

    with c2:
        st.markdown("**Reference payload**")
        if expected_payload.strip():
            if expected_format in {"oai_dc_xml", "datacite_xml", "openaire_xml"}:
                st.code(_pretty_xml(expected_payload), language="xml")
            else:
                st.code(expected_payload, language="text")
        else:
            st.caption("No reference payload provided.")

    with st.expander("Advanced: Parsed IR", expanded=False):
        st.subheader("Source IR")
        st.code(
            json.dumps(
                {k: [v.model_dump() for v in vals] for k, vals in source_ir.items()},
                indent=2,
            ),
            language="json",
        )
        st.subheader("Converted IR")
        st.code(
            json.dumps(
                {k: [v.model_dump() for v in vals] for k, vals in converted_ir.items()},
                indent=2,
            ),
            language="json",
        )
