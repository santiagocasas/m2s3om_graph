from pathlib import Path

import streamlit as st

from kaigraph.db import CrosswalkStore, build_default_store
from kaigraph.rdamsc import (
    backfill_kg_from_sssom,
    load_pipeline_status,
    sync_rdamsc_catalog,
)

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SSSOM_DIR = BASE_DIR / "exports" / "sssom"
DEFAULT_OAI_BASE_URL = "https://elib.dlr.de/cgi/oai2"
DEFAULT_OAI_IDENTIFIER = "oai:elib.dlr.de:19460"
DEFAULT_OAI_PREFIX = "oai_dc"


def get_store() -> CrosswalkStore:
    if "crosswalk_store" not in st.session_state:
        st.session_state["crosswalk_store"] = build_default_store()
    return st.session_state["crosswalk_store"]


def ensure_seeded() -> None:
    if st.session_state.get("store_seeded"):
        return

    out_dir = sssom_dir()
    store = get_store()
    seeded_rules = 0

    if not store.list_crosswalks():
        try:
            _ = sync_rdamsc_catalog(store)
        except Exception:
            st.session_state["store_seeded"] = True
            return

    status_map = load_pipeline_status()
    for crosswalk in store.list_crosswalks():
        status = status_map.get(crosswalk.id, {}).get("status")
        if status not in {"ready", "kg_out_of_sync"}:
            continue
        path = out_dir / f"{crosswalk.id}.sssom.tsv"
        if not path.exists():
            continue
        bundle = store.get_crosswalk_bundle(crosswalk.id)
        if bundle is not None and bundle.rules:
            continue
        seeded_rules += backfill_kg_from_sssom(store, crosswalk, out_dir)

    st.session_state["store_seeded"] = True
    st.session_state["store_seeded_rules"] = seeded_rules


def sssom_dir() -> Path:
    DEFAULT_SSSOM_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_SSSOM_DIR
