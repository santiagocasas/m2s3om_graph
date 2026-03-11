import json
from xml.dom import minidom

import streamlit as st

from state import DEFAULT_OAI_BASE_URL, DEFAULT_OAI_IDENTIFIER, get_store, sssom_dir
from kaigraph.crosswalk import (
    ConversionStep,
    available_target_formats,
    matched_standards_for_format,
    resolve_conversion_route,
)
from kaigraph.interop import parse_openaire_xml_to_ir
from kaigraph.oai import (
    InstitutionEndpoint,
    MetadataFormatInfo,
    OAIClient,
    ResolvedFormat,
    bridge_metadata_format,
    load_demo_identifiers,
    load_institution_endpoints,
    parse_identifiers,
    parse_metadata_formats,
)
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


def _parse_payload(
    payload: str, payload_format: str, source_profile: str | None = None
):
    if payload_format == "oai_dc_xml":
        return parse_oai_dc_xml_to_ir(payload)
    if source_profile == "oai_openaire":
        return parse_openaire_xml_to_ir(payload)
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


def _institution_options() -> list[InstitutionEndpoint]:
    institutions = load_institution_endpoints()
    if not institutions:
        return [InstitutionEndpoint(name="DLR", oai_endpoint=DEFAULT_OAI_BASE_URL)]
    return institutions


def _resolved_formats_table(
    store, metadata_formats: list[MetadataFormatInfo]
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in metadata_formats:
        resolved = bridge_metadata_format(item)
        internal = resolved.internal_format if resolved is not None else "unsupported"
        catalog_matches = "-"
        targets = "-"
        note = resolved.note if resolved is not None else "No parser/route wired yet"
        if resolved is not None:
            standards = matched_standards_for_format(store, resolved.internal_format)
            catalog_matches = ", ".join(standard.name for standard in standards) or "-"
            target_formats = available_target_formats(
                store, resolved.internal_format, sssom_dir()
            )
            targets = ", ".join(FORMAT_OPTIONS[key] for key in target_formats) or "-"
        rows.append(
            {
                "metadataPrefix": item.metadata_prefix,
                "namespace/schema": item.metadata_namespace or item.schema or "-",
                "mapped format": FORMAT_OPTIONS.get(internal, internal),
                "catalog matches": catalog_matches,
                "can convert to": targets,
                "note": note or "-",
            }
        )
    return rows


def _resolved_choices(
    metadata_formats: list[MetadataFormatInfo],
) -> dict[str, ResolvedFormat]:
    out: dict[str, ResolvedFormat] = {}
    for item in metadata_formats:
        resolved = bridge_metadata_format(item)
        if resolved is None:
            continue
        out[item.metadata_prefix] = resolved
    return out


def _discover_formats(endpoint: str) -> list[MetadataFormatInfo]:
    client = OAIClient(endpoint)
    return parse_metadata_formats(client.list_metadata_formats())


def _load_sample_identifiers(
    institution_name: str,
    endpoint: str,
    metadata_prefix: str,
) -> tuple[list[str], str | None]:
    try:
        client = OAIClient(endpoint)
        xml_text = client.list_identifiers(metadata_prefix)
        result = parse_identifiers(xml_text, limit=8)
        if result.identifiers:
            return result.identifiers, None
    except Exception as exc:
        error = str(exc)
    else:
        error = "No identifiers returned"

    fallback = (
        load_demo_identifiers().get(institution_name, {}).get(metadata_prefix, [])
    )
    if fallback:
        return (
            fallback,
            f"Live identifier lookup failed; using curated fallback. ({error})",
        )
    return [], error


def _repository_source_panel(store) -> tuple[str, str | None, str, str | None]:
    institutions = _institution_options()
    names = [item.name for item in institutions]
    default_index = names.index("DLR") if "DLR" in names else 0
    institution_name = st.selectbox(
        "Institution", [*names, "Custom endpoint"], index=default_index
    )

    selected_endpoint = next(
        (item.oai_endpoint for item in institutions if item.name == institution_name),
        DEFAULT_OAI_BASE_URL,
    )
    endpoint = st.text_input(
        "OAI-PMH endpoint",
        value=selected_endpoint
        if institution_name != "Custom endpoint"
        else DEFAULT_OAI_BASE_URL,
    )

    st.caption(
        "`oai_openaire` is treated as DataCite-compatible in this demo. After discovery, the app shows which OAI formats it can actually map to the RDAMSC/SSSOM catalog."
    )

    if st.button(
        "Discover metadata formats", key="transform_discover_formats", type="primary"
    ):
        try:
            st.session_state["transform_discovered_formats"] = _discover_formats(
                endpoint
            )
            st.session_state["transform_discovery_endpoint"] = endpoint
            st.success(
                f"Found {len(st.session_state['transform_discovered_formats'])} metadata formats."
            )
        except Exception as exc:
            st.error(f"Format discovery failed: {exc}")

    discovered = st.session_state.get("transform_discovered_formats", [])
    if endpoint != st.session_state.get("transform_discovery_endpoint"):
        discovered = []

    if discovered:
        st.dataframe(
            _resolved_formats_table(store, discovered),
            use_container_width=True,
            hide_index=True,
        )

    choices = _resolved_choices(discovered)
    if not choices:
        st.info(
            "Discover metadata formats first. Supported source families are Dublin Core and DataCite/OpenAIRE."
        )
        return "", None, endpoint, None

    selected_prefix = st.selectbox(
        "Source metadataPrefix",
        list(choices.keys()),
        format_func=lambda prefix: f"{prefix} -> {FORMAT_OPTIONS[choices[prefix].internal_format]}",
    )
    resolved = choices[selected_prefix]

    if st.button("Load sample record IDs", key="transform_load_identifiers"):
        identifiers, warning = _load_sample_identifiers(
            institution_name, endpoint, selected_prefix
        )
        st.session_state["transform_identifier_choices"] = identifiers
        if identifiers:
            st.session_state["transform_record_identifier"] = identifiers[0]
        if warning:
            st.warning(warning)
        elif identifiers:
            st.success(f"Loaded {len(identifiers)} sample identifiers.")

    identifier_choices = st.session_state.get("transform_identifier_choices", [])
    if identifier_choices:
        picked = st.selectbox(
            "Suggested record identifiers",
            identifier_choices,
            key="transform_identifier_select",
        )
    else:
        picked = ""

    default_identifier = st.session_state.get(
        "transform_record_identifier", picked or DEFAULT_OAI_IDENTIFIER
    )
    identifier = st.text_input(
        "Record identifier / URI",
        value=str(default_identifier),
        key="transform_record_identifier",
    )

    if st.button("Fetch source record", key="transform_fetch_payload"):
        try:
            client = OAIClient(endpoint)
            payload = client.get_record(str(identifier), selected_prefix)
        except Exception as exc:
            st.error(f"Failed to fetch source payload: {exc}")
        else:
            st.session_state["transform_source_payload"] = payload
            st.session_state["transform_source_format"] = resolved.internal_format
            st.session_state["transform_source_profile"] = resolved.source_profile
            st.session_state["transform_source_label"] = selected_prefix

    return (
        st.session_state.get("transform_source_payload", ""),
        st.session_state.get("transform_source_format"),
        endpoint,
        st.session_state.get("transform_source_profile"),
    )


def _manual_source_panel() -> tuple[str, str | None, str | None]:
    source_format = st.selectbox(
        "Source payload format",
        options=list(FORMAT_OPTIONS.keys()),
        format_func=lambda key: FORMAT_OPTIONS[key],
    )
    source_payload = st.text_area(
        "Source payload",
        value="",
        height=260,
        placeholder="Paste an OAI Dublin Core or DataCite/OpenAIRE XML record here.",
    )
    source_profile = None
    if source_format == "datacite_xml":
        source_profile = st.selectbox(
            "DataCite family",
            options=["datacite", "oai_openaire"],
            format_func=lambda value: "OpenAIRE (DataCite-compatible)"
            if value == "oai_openaire"
            else "DataCite",
        )
    return source_payload, source_format, source_profile


def _render_result(
    source_payload: str, source_label: str, target_format: str, transformed_payload: str
) -> None:
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
            "Download converted payload", transformed_payload, file_name=file_name
        )


def render() -> None:
    st.header("Convert One Record")
    st.caption(
        "Choose a Helmholtz repository, inspect the metadata formats it exposes, fetch one record, and convert it using the authoritative SSSOM route."
    )
    st.info(
        "This demo currently supports Dublin Core and DataCite-family payloads. OpenAIRE is handled as DataCite-compatible."
    )

    store = get_store()
    source_mode = st.radio(
        "Source workflow",
        ["Repository browser", "Paste manually"],
        horizontal=True,
    )

    source_payload = ""
    source_format: str | None = None
    source_profile: str | None = None
    source_label = ""

    if source_mode == "Repository browser":
        source_payload, source_format, _, source_profile = _repository_source_panel(
            store
        )
        source_label = st.session_state.get("transform_source_label", "OAI-PMH")
    else:
        source_payload, source_format, source_profile = _manual_source_panel()
        source_label = (
            "OpenAIRE (DataCite-compatible)"
            if source_profile == "oai_openaire"
            else FORMAT_OPTIONS.get(source_format or "", "Manual XML")
        )

    if source_format is None:
        return

    target_options = available_target_formats(store, source_format, sssom_dir())
    if not target_options:
        st.warning(
            "No authoritative conversion target is available for the selected source format yet."
        )
        return

    target_format = st.selectbox(
        "Convert to",
        options=target_options,
        format_func=lambda key: FORMAT_OPTIONS[key],
    )

    steps = resolve_conversion_route(store, source_format, target_format, sssom_dir())
    _render_route(steps, source_format, target_format)

    if not st.button("Convert record", key="transform_convert_record"):
        return
    if not source_payload.strip():
        st.warning("Provide or fetch a source payload first.")
        return

    try:
        source_ir = _parse_payload(source_payload, source_format, source_profile)
        converted_ir, report = _apply_conversion_steps(source_ir, steps)
        transformed_payload = _serialize_target(converted_ir, target_format)
    except Exception as exc:
        st.error(f"Conversion failed: {exc}")
        return

    c1, c2, c3 = st.columns(3)
    c1.metric("Applied rules", str(len(report.applied_rule_ids)))
    c2.metric("Unmapped fields", str(len(report.unmapped_fields)))
    c3.metric("Semantic loss rules", str(len(report.semantic_loss_rules)))

    _render_result(source_payload, source_label, target_format, transformed_payload)

    with st.expander("Transformation details", expanded=False):
        st.json(
            {
                "source_format": source_format,
                "source_profile": source_profile,
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
