import streamlit as st

from views import crosswalks, pipeline, system, transform
from state import ensure_seeded


def main() -> None:
    st.set_page_config(page_title="m2s3om_graph crosswalks", layout="wide")
    st.title("Evidence-Based Metadata Crosswalk Workbench")
    st.caption(
        "Authoritative mapping rules + explainable conversion + AI-assisted candidate suggestions."
    )
    st.caption("Workflow: 1) Browse mappings  2) Run pipeline  3) Convert records")
    system.render_sidebar()
    ensure_seeded()

    tab1, tab2, tab3 = st.tabs(
        [
            "1) Crosswalk Browser",
            "2) Pipeline",
            "3) Convert One Record",
        ]
    )
    with tab1:
        crosswalks.render()
    with tab2:
        pipeline.render()
    with tab3:
        transform.render()


if __name__ == "__main__":
    main()
