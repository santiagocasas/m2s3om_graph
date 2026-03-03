import os

import streamlit as st


def render() -> None:
    st.header("System")
    st.caption("Runtime hints for SurrealDB + Blablador integration.")

    st.markdown("### SurrealDB")
    st.write(f"`KAIGRAPH_USE_SURREAL={os.getenv('KAIGRAPH_USE_SURREAL', '0')}`")
    st.write(
        f"`KAIGRAPH_DB_URL={os.getenv('KAIGRAPH_DB_URL', 'ws://localhost:8000/rpc')}`"
    )
    st.write(f"`KAIGRAPH_DB_NS={os.getenv('KAIGRAPH_DB_NS', 'kaigraph')}`")
    st.write(f"`KAIGRAPH_DB_NAME={os.getenv('KAIGRAPH_DB_NAME', 'crosswalk')}`")

    st.markdown("### Blablador")
    has_key = bool(os.getenv("BLABLADOR_API_KEY"))
    st.write(f"API key loaded: `{has_key}`")
    st.write(
        "`BLABLADOR_BASE_URL=`"
        + os.getenv(
            "BLABLADOR_BASE_URL",
            "https://api.helmholtz-blablador.fz-juelich.de/v1",
        )
    )
    st.write(
        "`KAIGRAPH_LLM_MODEL=`"
        + os.getenv(
            "KAIGRAPH_LLM_MODEL",
            "alias-fast",
        )
    )

    st.markdown("### Artifact Conversion")
    st.write("Using MarkItDown for artifact-to-markdown conversion.")
