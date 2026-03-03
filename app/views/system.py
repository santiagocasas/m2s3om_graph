import os

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


def render_sidebar() -> None:
    rows = _env_rows()
    st.sidebar.markdown("### System")
    st.sidebar.caption("Runtime diagnostics")
    st.sidebar.write(f"DB URL: `{rows['KAIGRAPH_DB_URL']}`")
    st.sidebar.write(
        f"Namespace/DB: `{rows['KAIGRAPH_DB_NS']}/{rows['KAIGRAPH_DB_NAME']}`"
    )
    st.sidebar.write(f"Blablador key: `{rows['BLABLADOR_API_KEY']}`")
    st.sidebar.write(f"Model: `{rows['KAIGRAPH_LLM_MODEL']}`")

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
