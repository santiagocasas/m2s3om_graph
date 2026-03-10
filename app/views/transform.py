import json
from xml.dom import minidom

import streamlit as st

from state import DEFAULT_OAI_BASE_URL, DEFAULT_OAI_IDENTIFIER, get_store, sssom_dir
from kaigraph.crosswalk import ConversionStep, resolve_conversion_route
from kaigraph.oai import OAIClient, parse_metadata_prefixes
from kaigraph.transform import (
    TransformationReport,
    apply_mapping_rules,
    ir_to_datacite_xml,
    ir_to_dublin_core_xml,
    parse_datacite_xml_to_ir,
    parse_oai_dc_xml_to_ir,
)

FORMAT_OPTIONS = {
    "oai_dc_xml": "OAI Dublin Core XML",
    "datacite_xml": "DataCite XML",
}


def _pretty_xml(xml_text: str) -> str:
    try:
        parsed = minidom.parseString(xml_text)
        return parsed.toprettyxml(indent="  ")
    except Exception:
        return xml_text


def _to_internal_format(metadata_prefix: str) -> str | None:
    value = metadata_prefix.strip().lower()
    if value == "oai_dc":
        return "oai_dc_xml"
    if "datacite" in value:
        return "datacite_xml"
    return None


def _parse_payload(payload: str, payload_format: str):
    if payload_format == "oai_dc_xml":
        return parse_oai_dc_xml_to_ir(payload)
    if payload_format == "datacite_xml":
        return parse_datacite_xml_to_ir(payload)
    raise ValueError(f"Unsupported format: {payload_format}")


def _serialize_target(target_ir, target_format: str) -> str:
    if target_format == "oai_dc_xml":
        return ir_to_dublin_core_xml(target_ir)
    if target_format == "datacite_xml":
        return ir_to_datacite_xml(target_ir)
    raise ValueError(f"Unsupported target format: {target_format}")


def _merge_reports(reports: list[TransformationReport]) -> TransformationReport:
    merged = TransformationReport()
    for report in reports:
        merged.applied_rule_ids.extend(report.applied_rule_ids)
        merged.unmapped_fields.extend(report.unmapped_fields)
        merged.semantic_loss_rules.extend(report.semantic_loss_rules)
        merged.ambiguous_rules.extend(report.ambiguous_rules)

    merged.applied_rule_ids = sorted(set(merged.applied_rule_ids))
    merged.unmapped_fields = sorted(set(merged.unmapped_fields))
    merged.semantic_loss_rules = sorted(set(merged.semantic_loss_rules))
    merged.ambiguous_rules = sorted(set(merged.ambiguous_rules))
    return merged


def _apply_conversion_steps(source_ir, steps: list[ConversionStep]):
    current_ir = source_ir
    reports: list[TransformationReport] = []
    for step in steps:
        current_ir, report = apply_mapping_rules(current_ir, step.rules)
        reports.append(report)
    return current_ir, _merge_reports(reports)


def _route_caption(
    steps: list[ConversionStep], source_format: str, target_format: str
) -> str:
    if source_format == target_format:
        return "No mapping chain needed; the source is already in the selected target format."
    if not steps:
        return "No authoritative SSSOM route is available for this format pair yet."
    labels = [
        f"{step.crosswalk_name} ({'reverse' if step.direction == 'reverse' else 'forward'})"
        for step in steps
    ]
    return " -> ".join(labels)


def _render_route(
    steps: list[ConversionStep], source_format: str, target_format: str
) -> None:
    st.subheader("Route")
    st.caption(_route_caption(steps, source_format, target_format))
    if not steps:
        return
    st.table(
        [
            {
                "crosswalk": step.crosswalk_id,
                "name": step.crosswalk_name,
                "direction": step.direction,
                "rules": len(step.rules),
            }
            for step in steps
        ]
    )


def _load_from_oai() -> tuple[str, str | None, str]:
    base_url = st.text_input("OAI-PMH base URL", value=DEFAULT_OAI_BASE_URL)
    identifier = st.text_input("Record identifier / URI", value=DEFAULT_OAI_IDENTIFIER)

    prefixes_key = "transform_prefixes"
    if prefixes_key not in st.session_state:
        st.session_state[prefixes_key] = ["oai_dc"]

    if st.button("Discover metadata formats", key="transform_discover_formats"):
        try:
            client = OAIClient(base_url)
            prefixes = parse_metadata_prefixes(client.list_metadata_formats(identifier))
            st.session_state[prefixes_key] = prefixes or ["oai_dc"]
            st.success(f"Found {len(st.session_state[prefixes_key])} metadata formats.")
        except Exception as exc:
            st.error(f"Format discovery failed: {exc}")

    source_prefix = st.selectbox(
        "Source metadataPrefix",
        st.session_state[prefixes_key],
        key="transform_source_prefix",
    )

    if st.button("Fetch source record", key="transform_fetch_payload", type="primary"):
        try:
            client = OAIClient(base_url)
            payload = client.get_record(identifier, source_prefix)
        except Exception as exc:
            st.error(f"Failed to fetch source payload: {exc}")
        else:
            st.session_state["transform_source_payload"] = payload
            st.session_state["transform_source_format"] = _to_internal_format(
                source_prefix
            )

    payload = st.session_state.get("transform_source_payload", "")
    payload_format = st.session_state.get("transform_source_format")
    if payload:
        st.success("Source payload loaded.")
    return payload, payload_format, source_prefix


def render() -> None:
    st.header("Convert One Record")
    st.caption(
        "Fetch one OAI-PMH record or paste XML, then convert it with the authoritative SSSOM route."
    )
    st.info(
        "Today this tab is optimized for OAI Dublin Core and DataCite so the demo stays simple and reliable."
    )

    store = get_store()
    source_mode = st.radio(
        "Record source",
        ["Fetch from OAI-PMH", "Paste manually"],
        horizontal=True,
    )

    source_payload = ""
    source_format: str | None = None
    source_label = ""
    if source_mode == "Fetch from OAI-PMH":
        source_payload, source_format, source_label = _load_from_oai()
    else:
        source_format = st.selectbox(
            "Source payload format",
            options=list(FORMAT_OPTIONS.keys()),
            format_func=lambda key: FORMAT_OPTIONS[key],
        )
        source_payload = st.text_area(
            "Source payload",
            value="",
            height=260,
            placeholder="Paste an OAI Dublin Core or DataCite XML record here.",
        )
        source_label = FORMAT_OPTIONS[source_format]

    target_format = st.selectbox(
        "Convert to",
        options=list(FORMAT_OPTIONS.keys()),
        format_func=lambda key: FORMAT_OPTIONS[key],
        index=1 if source_format == "oai_dc_xml" else 0,
    )

    steps = (
        resolve_conversion_route(store, source_format, target_format, sssom_dir())
        if source_format is not None
        else []
    )
    _render_route(steps, source_format or "", target_format)

    if not st.button("Convert record", key="transform_convert_record"):
        return

    if not source_payload.strip():
        st.warning("Provide or fetch a source payload first.")
        return
    if source_format is None:
        st.error(
            "The selected metadataPrefix is not supported yet in the demo app. Use `oai_dc` or a DataCite-compatible prefix."
        )
        return

    try:
        source_ir = _parse_payload(source_payload, source_format)
    except Exception as exc:
        st.error(f"Failed to parse source payload: {exc}")
        return

    if source_format != target_format and not steps:
        st.error("No authoritative SSSOM route is available for this conversion yet.")
        return

    try:
        if source_format == target_format:
            converted_ir = source_ir
            report = TransformationReport()
        else:
            converted_ir, report = _apply_conversion_steps(source_ir, steps)
        transformed_payload = _serialize_target(converted_ir, target_format)
    except Exception as exc:
        st.error(f"Conversion failed: {exc}")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Applied rules", str(len(report.applied_rule_ids)))
    c2.metric("Unmapped fields", str(len(report.unmapped_fields)))
    c3.metric("Semantic loss rules", str(len(report.semantic_loss_rules)))

    st.subheader("Result")
    left, right = st.columns(2)
    with left:
        st.markdown("**Source payload**")
        st.caption(source_label)
        st.code(_pretty_xml(source_payload), language="xml")
    with right:
        st.markdown("**Converted payload**")
        st.caption(FORMAT_OPTIONS[target_format])
        st.code(_pretty_xml(transformed_payload), language="xml")
        file_name = (
            "converted_dublincore.xml"
            if target_format == "oai_dc_xml"
            else "converted_datacite.xml"
        )
        st.download_button(
            "Download converted payload",
            transformed_payload,
            file_name=file_name,
        )

    with st.expander("Transformation details", expanded=False):
        st.json(
            {
                "source_format": source_format,
                "target_format": target_format,
                "route": [
                    {
                        "crosswalk_id": step.crosswalk_id,
                        "name": step.crosswalk_name,
                        "direction": step.direction,
                        "rules": len(step.rules),
                    }
                    for step in steps
                ],
                "applied_rules": report.applied_rule_ids,
                "unmapped_fields": report.unmapped_fields,
                "semantic_loss_rules": report.semantic_loss_rules,
                "ambiguous_rules": report.ambiguous_rules,
            }
        )

    with st.expander("Advanced: Parsed IR", expanded=False):
        st.subheader("Source IR")
        st.code(
            json.dumps(
                {
                    key: [value.model_dump() for value in values]
                    for key, values in source_ir.items()
                },
                indent=2,
            ),
            language="json",
        )
        st.subheader("Converted IR")
        st.code(
            json.dumps(
                {
                    key: [value.model_dump() for value in values]
                    for key, values in converted_ir.items()
                },
                indent=2,
            ),
            language="json",
        )
