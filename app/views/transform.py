import json
import re
from xml.dom import minidom

import streamlit as st

from state import (
    DEFAULT_OAI_BASE_URL,
    DEFAULT_OAI_IDENTIFIER,
    DEFAULT_OAI_PREFIX,
    get_store,
    sssom_dir,
)
from kaigraph.crosswalk import derive_reverse_rules
from kaigraph.db import CrosswalkBundle
from kaigraph.interop import (
    elib_export_urls,
    fetch_export,
    parse_dc_export_text_to_ir,
    parse_openaire_xml_to_ir,
)
from kaigraph.oai import OAIClient, parse_metadata_prefixes
from kaigraph.benchmark.metrics import compare_ir
from kaigraph.transform import (
    apply_mapping_rules,
    ir_to_datacite_xml,
    ir_to_dublin_core_xml,
    parse_oai_dc_xml_to_ir,
)
from kaigraph.rdamsc import ensure_sssom_for_bundle, sssom_output_path
from kaigraph.sssom import load_sssom_rules


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


def render() -> None:
    st.header("Transform a record")
    st.caption(
        "Fetch one record, convert it using a selected crosswalk, and inspect the transformation report."
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
        format_func=lambda x: f"{x.name} ({x.id})",
        key="transform_crosswalk_select",
    )

    tab_convert, tab_compare = st.tabs(["OAI-PMH Convert", "eLib Export Compare"])

    with tab_convert:
        base_url = st.text_input("OAI-PMH base URL", value=DEFAULT_OAI_BASE_URL)
        record_url = st.text_input(
            "eLib record URL (optional)",
            value="",
            placeholder="https://elib.dlr.de/204960/",
        )
        suggested_identifier = DEFAULT_OAI_IDENTIFIER
        if record_url.strip():
            match = re.search(r"elib\.dlr\.de/(\d+)", record_url)
            if match:
                suggested_identifier = f"oai:elib.dlr.de:{match.group(1)}"
                st.caption(f"Suggested OAI identifier: `{suggested_identifier}`")
        identifier = st.text_input("Identifier", value=suggested_identifier)
        metadata_prefix = st.text_input("MetadataPrefix", value=DEFAULT_OAI_PREFIX)
        use_reverse = st.checkbox(
            "Use derived reverse mapping (best effort)", value=False
        )

        if st.button("Fetch metadata formats"):
            try:
                client = OAIClient(base_url)
                xml_text = client.list_metadata_formats(identifier)
                prefixes = parse_metadata_prefixes(xml_text)
                st.write(prefixes)
            except Exception as exc:
                st.error(f"Failed to list metadata formats: {exc}")

        if not st.button("Fetch and transform", type="primary"):
            pass
        else:
            try:
                client = OAIClient(base_url)
                xml_text = client.get_record(identifier, metadata_prefix)
            except Exception as exc:
                st.error(f"Failed to fetch record: {exc}")
                return

            try:
                source_ir = parse_oai_dc_xml_to_ir(xml_text)
            except Exception as exc:
                st.error(f"Failed to parse oai_dc record: {exc}")
                return

            bundle = store.get_crosswalk_bundle(selected_crosswalk.id)
            if bundle is None:
                st.error("Crosswalk not found")
                return
            base_rules = _authoritative_rules(bundle)
            if use_reverse:
                working_rules = derive_reverse_rules(
                    bundle.model_copy(update={"rules": base_rules})
                )
            else:
                working_rules = base_rules

            target_ir, report = apply_mapping_rules(source_ir, working_rules)

            st.subheader("Transformation report")
            st.json(
                {
                    "applied_rules": report.applied_rule_ids,
                    "unmapped_fields": report.unmapped_fields,
                    "semantic_loss_rules": report.semantic_loss_rules,
                    "ambiguous_rules": report.ambiguous_rules,
                }
            )

            with st.expander("Advanced: Source and target IR", expanded=False):
                st.subheader("Source IR")
                st.code(
                    json.dumps(
                        {
                            k: [v.model_dump() for v in vals]
                            for k, vals in source_ir.items()
                        },
                        indent=2,
                    ),
                    language="json",
                )
                st.subheader("Target IR")
                st.code(
                    json.dumps(
                        {
                            k: [v.model_dump() for v in vals]
                            for k, vals in target_ir.items()
                        },
                        indent=2,
                    ),
                    language="json",
                )

            if use_reverse:
                transformed_xml = ir_to_datacite_xml(target_ir)
                outfile = "transformed_datacite.xml"
            else:
                transformed_xml = ir_to_dublin_core_xml(target_ir)
                outfile = "transformed_dublincore.xml"

            st.subheader("Transformed XML")
            st.code(_pretty_xml(transformed_xml), language="xml")
            st.download_button(
                "Download transformed XML", transformed_xml, file_name=outfile
            )

    with tab_compare:
        st.subheader("Compare with eLib Export URLs")
        st.caption(
            "Fetches OpenAIRE XML and Dublin Core export for one eLib record and compares converted output to endpoint ground truth."
        )
        record_id = st.text_input("eLib record ID", value="204960")
        compare_direction = st.radio(
            "Comparison direction",
            ["OpenAIRE -> Dublin Core", "Dublin Core -> DataCite"],
            horizontal=True,
        )
        urls = elib_export_urls(record_id)
        st.markdown(f"- OpenAIRE: `{urls['openaire']}`")
        st.markdown(f"- Dublin Core: `{urls['dublin_core']}`")

        if not st.button("Run export comparison"):
            return

        try:
            openaire_xml = fetch_export(urls["openaire"])
            dc_text = fetch_export(urls["dublin_core"])
        except Exception as exc:
            st.error(f"Failed to fetch exports: {exc}")
            return
        with st.expander("Raw endpoint exports", expanded=False):
            left, right = st.columns(2)
            with left:
                st.subheader("Raw OpenAIRE XML")
                st.code(_pretty_xml(openaire_xml), language="xml")
            with right:
                st.subheader("Raw Dublin Core export")
                st.code(dc_text, language="text")

        bundle = store.get_crosswalk_bundle(selected_crosswalk.id)
        if bundle is None:
            st.error("Crosswalk not found")
            return
        base_rules = _authoritative_rules(bundle)

        if compare_direction == "OpenAIRE -> Dublin Core":
            source_ir = parse_openaire_xml_to_ir(openaire_xml)
            expected_ir = parse_dc_export_text_to_ir(dc_text)
            converted_ir, report = apply_mapping_rules(source_ir, base_rules)
            converted_xml = ir_to_dublin_core_xml(converted_ir)
            converted_title = "Converted Dublin Core XML"
            expected_title = "Ground Truth Dublin Core XML"
            expected_xml = ir_to_dublin_core_xml(expected_ir)
        else:
            source_ir = parse_dc_export_text_to_ir(dc_text)
            expected_ir = parse_openaire_xml_to_ir(openaire_xml)
            reverse_rules = derive_reverse_rules(
                bundle.model_copy(update={"rules": base_rules})
            )
            converted_ir, report = apply_mapping_rules(source_ir, reverse_rules)
            converted_xml = ir_to_datacite_xml(converted_ir)
            converted_title = "Converted DataCite XML (best effort)"
            expected_title = "Ground Truth OpenAIRE/DataCite XML"
            expected_xml = openaire_xml

        coverage, overlap, metrics = compare_ir(converted_ir, expected_ir)

        c1, c2, c3 = st.columns(3)
        c1.metric("Field coverage", f"{coverage:.2f}")
        c2.metric("Value overlap", f"{overlap:.2f}")
        c3.metric("Unmapped fields", str(len(report.unmapped_fields)))

        st.subheader("Field-by-field comparison")
        for item in metrics:
            st.write(
                f"- {item.field}: expected={len(item.expected_values)}, actual={len(item.actual_values)}, overlap={item.normalized_overlap:.2f}, missing={len(item.missing_values)}, extra={len(item.extra_values)}"
            )

        st.subheader("Side-by-side XML")
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**{converted_title}**")
            st.code(_pretty_xml(converted_xml), language="xml")
        with col_b:
            st.markdown(f"**{expected_title}**")
            st.code(_pretty_xml(expected_xml), language="xml")
