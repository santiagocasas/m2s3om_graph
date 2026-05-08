from pathlib import Path

from m2s3om_graph.crosswalk.route import resolve_conversion_route
from m2s3om_graph.db import InMemoryCrosswalkStore
from m2s3om_graph.ingest.crosswalk_ingestion import ingest_datacite_to_dc_pdf
from m2s3om_graph.rdamsc.ingest import ensure_sssom_for_bundle


def test_resolve_conversion_route_for_datacite_and_dc(
    datacite_mapping_pdf_path: Path,
) -> None:
    store = InMemoryCrosswalkStore()
    crosswalk_id = ingest_datacite_to_dc_pdf(store, datacite_mapping_pdf_path)
    bundle = store.get_crosswalk_bundle(crosswalk_id)
    assert bundle is not None

    output_dir = Path("/tmp/m2s3om_graph_route_test")
    _ = ensure_sssom_for_bundle(bundle, output_dir)

    forward = resolve_conversion_route(store, "datacite_xml", "oai_dc_xml", output_dir)
    reverse = resolve_conversion_route(store, "oai_dc_xml", "datacite_xml", output_dir)

    assert len(forward) == 1
    assert forward[0].direction == "forward"
    assert len(reverse) == 1
    assert reverse[0].direction == "reverse"
