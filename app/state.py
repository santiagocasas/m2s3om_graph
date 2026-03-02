from pathlib import Path

import streamlit as st

from kaigraph.db import CrosswalkStore, build_default_store

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
    _ = sssom_dir()


def sssom_dir() -> Path:
    DEFAULT_SSSOM_DIR.mkdir(parents=True, exist_ok=True)
    return DEFAULT_SSSOM_DIR
