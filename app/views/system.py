import os

import requests
import streamlit as st


def _env_rows() -> dict[str, str]:
    has_key = bool(os.getenv("BLABLADOR_API_KEY"))
    return {
        "KAIGRAPH_USE_SURREAL": os.getenv("KAIGRAPH_USE_SURREAL", "0"),
        "KAIGRAPH_DB_URL": os.getenv("KAIGRAPH_DB_URL", "ws://localhost:8000/rpc"),
        "KAIGRAPH_DB_NS": os.getenv("KAIGRAPH_DB_NS", "kaigraph"),
        "KAIGRAPH_DB_NAME": os.getenv("KAIGRAPH_DB_NAME", "crosswalk"),
        "BLABLADOR_API_KEY": "loaded" if has_key else "missing",
        "BLABLADOR_BASE_URL": os.getenv(
            "BLABLADOR_BASE_URL",
            "https://api.helmholtz-blablador.fz-juelich.de/v1",
        ),
        "KAIGRAPH_LLM_MODEL": os.getenv("KAIGRAPH_LLM_MODEL", "alias-fast"),
    }


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/") + "/"


@st.cache_data(ttl=300)
def _fetch_blablador_models_cached(
    base_url: str, api_key: str
) -> tuple[list[str], str | None]:
    if not api_key.strip():
        return [], "BLABLADOR_API_KEY is missing"
    try:
        response = requests.get(
            f"{_normalize_base_url(base_url)}models",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return [], str(exc)

    items = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return [], "Unexpected /models response"
    models: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        model_id = item.get("id")
        if isinstance(model_id, str) and model_id.strip():
            models.append(model_id.strip())
    models = sorted(set(models))
    if not models:
        return [], "No model IDs returned"
    return models, None


def _render_model_selector(use_sidebar: bool) -> None:
    rows = _env_rows()
    target = st.sidebar if use_sidebar else st
    key_prefix = "sidebar" if use_sidebar else "main"
    loaded_key = f"{key_prefix}_models_loaded"

    target.markdown("### Blablador Model")
    target.caption("Load the remote model list only when you need to run extraction.")

    if target.button("Load/refresh model list", key=f"{key_prefix}_refresh_models"):
        _fetch_blablador_models_cached.clear()
        st.session_state[loaded_key] = True

    default_model = st.session_state.get(
        "selected_blablador_model",
        rows["KAIGRAPH_LLM_MODEL"],
    )

    if not st.session_state.get(loaded_key, False):
        selected = target.text_input(
            "Active model",
            value=str(default_model),
            key=f"{key_prefix}_blablador_model_manual",
        )
        st.session_state["selected_blablador_model"] = selected
        os.environ["KAIGRAPH_LLM_MODEL"] = selected
        target.caption(
            "Remote model discovery is skipped during startup for faster app load."
        )
        target.write(f"Using model: `{selected}`")
        return

    models, error = _fetch_blablador_models_cached(
        rows["BLABLADOR_BASE_URL"],
        os.getenv("BLABLADOR_API_KEY", ""),
    )

    selected = default_model
    if models:
        if selected not in models:
            selected = selected if isinstance(selected, str) and selected else models[0]
            if selected not in models:
                selected = models[0]
        selected = target.selectbox(
            "Active model",
            options=models,
            index=models.index(selected),
            key=f"{key_prefix}_blablador_model",
        )
    else:
        selected = target.text_input(
            "Active model",
            value=str(default_model),
            key=f"{key_prefix}_blablador_model_manual",
        )
        if error:
            target.caption(f"Model list unavailable: {error}")

    st.session_state["selected_blablador_model"] = selected
    os.environ["KAIGRAPH_LLM_MODEL"] = selected
    target.write(f"Using model: `{selected}`")


def render_sidebar() -> None:
    rows = _env_rows()
    st.sidebar.markdown("### System")
    st.sidebar.caption("Runtime diagnostics")
    if not st.session_state.get("store_synced_catalog", False):
        st.sidebar.caption("Startup mode: local SSSOM snapshot (no catalog sync)")
    st.sidebar.write(f"DB URL: `{rows['KAIGRAPH_DB_URL']}`")
    st.sidebar.write(
        f"Namespace/DB: `{rows['KAIGRAPH_DB_NS']}/{rows['KAIGRAPH_DB_NAME']}`"
    )
    st.sidebar.write(f"Blablador key: `{rows['BLABLADOR_API_KEY']}`")
    _render_model_selector(use_sidebar=True)

    with st.sidebar.expander("Full runtime variables", expanded=False):
        st.write(f"`KAIGRAPH_USE_SURREAL={rows['KAIGRAPH_USE_SURREAL']}`")
        st.write(f"`KAIGRAPH_DB_URL={rows['KAIGRAPH_DB_URL']}`")
        st.write(f"`KAIGRAPH_DB_NS={rows['KAIGRAPH_DB_NS']}`")
        st.write(f"`KAIGRAPH_DB_NAME={rows['KAIGRAPH_DB_NAME']}`")
        st.write(f"`BLABLADOR_API_KEY={rows['BLABLADOR_API_KEY']}`")
        st.write(f"`BLABLADOR_BASE_URL={rows['BLABLADOR_BASE_URL']}`")
        st.write(f"`KAIGRAPH_LLM_MODEL={rows['KAIGRAPH_LLM_MODEL']}`")
        st.caption("Artifacts are converted to markdown via MarkItDown.")


def render() -> None:
    st.header("System")
    st.caption(
        "System diagnostics have moved to the sidebar for quicker workflow access."
    )
    render_sidebar()
