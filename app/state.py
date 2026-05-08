import os
import re
from pathlib import Path

import streamlit as st
import yaml

from m2s3om_graph.db import (
    CrosswalkRecord,
    CrosswalkStore,
    StandardRecord,
    build_default_store,
)
from m2s3om_graph.errors import make_error_payload
from m2s3om_graph.rdamsc.ingest import (
    sssom_output_path,
    sync_rdamsc_catalog,
)
from m2s3om_graph.rdamsc.pipeline import (
    backfill_kg_from_sssom,
    load_pipeline_status,
)
from m2s3om_graph.sssom import load_sssom_rules

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SSSOM_DIR = BASE_DIR / "exports" / "sssom"
DEFAULT_OAI_BASE_URL = "https://elib.dlr.de/cgi/oai2"
DEFAULT_OAI_IDENTIFIER = "oai:elib.dlr.de:19460"
DEFAULT_OAI_PREFIX = "oai_dc"

DESCRIPTION_RE = re.compile(r"^(?P<crosswalk>.*) \((?P<source>.*) -> (?P<target>.*)\)$")


def _auto_sync_enabled() -> bool:
    value = os.getenv("M2S3OM_AUTO_SYNC_ON_START", "0").strip().lower()
    return value in {"1", "true", "yes", "on"}


def get_store() -> CrosswalkStore:
    store = st.session_state.get("crosswalk_store")
    if isinstance(store, CrosswalkStore):
        return store
    raise RuntimeError("Crosswalk store is not initialized. Call ensure_store() first.")


def ensure_store() -> CrosswalkStore:
    if "crosswalk_store" not in st.session_state:
        st.session_state["crosswalk_store"] = build_default_store()
    return get_store()


def _parse_sssom_metadata(path: Path) -> dict[str, object]:
    header_lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            break
        header_lines.append(line[1:])
    if not header_lines:
        return {}
    loaded = yaml.safe_load("\n".join(header_lines))
    if isinstance(loaded, dict):
        return loaded
    return {}


def _standard_id_from_curie_map(metadata: dict[str, object], key: str) -> str:
    curie_map = metadata.get("curie_map")
    if not isinstance(curie_map, dict):
        return key
    raw = curie_map.get(key)
    if not isinstance(raw, str):
        return key
    trimmed = raw.rstrip("/")
    return trimmed.rsplit("/", 1)[-1] or key


def _description_parts(metadata: dict[str, object]) -> tuple[str, str, str]:
    description = str(metadata.get("mapping_set_description", "")).strip()
    match = DESCRIPTION_RE.match(description)
    if match is not None:
        return (
            match.group("crosswalk").strip(),
            match.group("source").strip(),
            match.group("target").strip(),
        )
    return description or "Imported SSSOM crosswalk", "Source", "Target"


def _msc_id_from_crosswalk_id(crosswalk_id: str) -> str | None:
    if crosswalk_id.startswith("rdamsc_c"):
        return "msc:" + crosswalk_id.split("rdamsc_", 1)[1]
    return None


def _optional_str(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _seed_store_from_sssom_exports(store: CrosswalkStore, out_dir: Path) -> int:
    seeded_rules = 0
    for path in sorted(out_dir.glob("*.sssom.tsv")):
        metadata = _parse_sssom_metadata(path)
        mapping_set_id = str(metadata.get("mapping_set_id", "")).strip()
        if not mapping_set_id.startswith("m2s3om_graph:"):
            continue
        crosswalk_id = mapping_set_id.split(":", 1)[1]
        rules = load_sssom_rules(path, crosswalk_id)
        if not rules:
            continue

        crosswalk_name, source_name, target_name = _description_parts(metadata)
        source_standard_id = _standard_id_from_curie_map(metadata, "src")
        target_standard_id = _standard_id_from_curie_map(metadata, "dst")

        _ = store.upsert_standard(
            StandardRecord(
                id=source_standard_id,
                name=source_name,
                namespace=source_standard_id.split("_", 1)[0],
            )
        )
        _ = store.upsert_standard(
            StandardRecord(
                id=target_standard_id,
                name=target_name,
                namespace=target_standard_id.split("_", 1)[0],
            )
        )
        _ = store.upsert_crosswalk(
            CrosswalkRecord(
                id=crosswalk_id,
                name=crosswalk_name,
                source_standard_id=source_standard_id,
                target_standard_id=target_standard_id,
                version=_optional_str(metadata.get("mapping_set_version")),
                doc_uri=_optional_str(metadata.get("mapping_set_source")),
                msc_id=_msc_id_from_crosswalk_id(crosswalk_id),
            )
        )
        for rule in rules:
            _ = store.upsert_mapping_rule(rule)
        seeded_rules += len(rules)
    return seeded_rules


def ensure_seeded() -> None:
    if st.session_state.get("store_seeded"):
        return

    out_dir = sssom_dir()
    store = ensure_store()
    seeded_rules = _seed_store_from_sssom_exports(store, out_dir)
    synced_catalog = False

    if not store.list_crosswalks() and _auto_sync_enabled():
        try:
            _ = sync_rdamsc_catalog(store)
            synced_catalog = True
            st.session_state["store_sync_error"] = None
        except Exception as exc:
            diagnostics = getattr(exc, "diagnostics", None)
            if isinstance(diagnostics, dict):
                st.session_state["store_sync_error"] = diagnostics
            else:
                st.session_state["store_sync_error"] = make_error_payload(
                    source="app_state",
                    operation="ensure_seeded.sync_rdamsc_catalog",
                    error=exc,
                )
            st.session_state["store_seeded"] = True
            st.session_state["store_seeded_rules"] = seeded_rules
            st.session_state["store_synced_catalog"] = False
            return

    status_map = load_pipeline_status()
    for crosswalk in store.list_crosswalks():
        status = status_map.get(crosswalk.id, {}).get("status")
        if status not in {"ready", "kg_out_of_sync"}:
            continue
        path = sssom_output_path(out_dir, crosswalk.id)
        if not path.exists():
            continue
        bundle = store.get_crosswalk_bundle(crosswalk.id)
        if bundle is not None and bundle.rules:
            continue
        seeded_rules += backfill_kg_from_sssom(store, crosswalk, out_dir)

    st.session_state["store_seeded"] = True
    st.session_state["store_seeded_rules"] = seeded_rules
    st.session_state["store_synced_catalog"] = synced_catalog


def sssom_dir() -> Path:
    DEFAULT_SSSOM_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_SSSOM_DIR
