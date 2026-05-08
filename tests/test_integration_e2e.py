from pathlib import Path

from m2s3om_graph.db import InMemoryCrosswalkStore
from m2s3om_graph.ingest.crosswalk_ingestion import ingest_datacite_to_dc_pdf
from m2s3om_graph.transform.apply import apply_mapping_rules
from m2s3om_graph.transform.parsers import parse_oai_dc_xml_to_ir
from m2s3om_graph.transform.serializers import ir_to_dublin_core_xml


def test_end_to_end_ingest_and_transform(datacite_mapping_pdf_path: Path) -> None:
    store = InMemoryCrosswalkStore()
    crosswalk_id = ingest_datacite_to_dc_pdf(store, datacite_mapping_pdf_path)
    bundle = store.get_crosswalk_bundle(crosswalk_id)
    assert bundle is not None
    assert len(bundle.rules) > 20

    xml_text = Path("tests/fixtures/oai_getrecord_dc.xml").read_text(encoding="utf-8")
    source_ir = parse_oai_dc_xml_to_ir(xml_text)
    target_ir, report = apply_mapping_rules(source_ir, bundle.rules)
    output_xml = ir_to_dublin_core_xml(target_ir)

    assert "oai_dc:dc" in output_xml
    assert isinstance(report.applied_rule_ids, list)
