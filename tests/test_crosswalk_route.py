from pathlib import Path

from kaigraph.crosswalk import resolve_conversion_route
from kaigraph.db import InMemoryCrosswalkStore
from kaigraph.ingest import ingest_datacite_to_dc_pdf
from kaigraph.rdamsc import ensure_sssom_for_bundle


def test_resolve_conversion_route_for_datacite_and_dc() -> None:
    store = InMemoryCrosswalkStore()
    pdf_path = Path("/home/casas/AI/Metadata-Mappings/DataCite_DublinCore_Mapping.pdf")
    if not pdf_path.exists():
        return

    crosswalk_id = ingest_datacite_to_dc_pdf(store, pdf_path)
    bundle = store.get_crosswalk_bundle(crosswalk_id)
    assert bundle is not None

    output_dir = Path("/tmp/kaigraph_route_test")
    _ = ensure_sssom_for_bundle(bundle, output_dir)

    forward = resolve_conversion_route(store, "datacite_xml", "oai_dc_xml", output_dir)
    reverse = resolve_conversion_route(store, "oai_dc_xml", "datacite_xml", output_dir)

    assert len(forward) == 1
    assert forward[0].direction == "forward"
    assert len(reverse) == 1
    assert reverse[0].direction == "reverse"
