from pathlib import Path

from kaigraph.db import InMemoryCrosswalkStore
from kaigraph.ingest import ingest_datacite_to_dc_pdf
from kaigraph.transform import (
    apply_mapping_rules,
    ir_to_dublin_core_xml,
    parse_oai_dc_xml_to_ir,
)


def test_end_to_end_ingest_and_transform() -> None:
    store = InMemoryCrosswalkStore()
    pdf_path = Path("/home/casas/AI/Metadata-Mappings/DataCite_DublinCore_Mapping.pdf")
    if not pdf_path.exists():
        return

    crosswalk_id = ingest_datacite_to_dc_pdf(store, pdf_path)
    bundle = store.get_crosswalk_bundle(crosswalk_id)
    assert bundle is not None
    assert len(bundle.rules) > 20

    xml_text = Path("tests/fixtures/oai_getrecord_dc.xml").read_text(encoding="utf-8")
    source_ir = parse_oai_dc_xml_to_ir(xml_text)
    target_ir, report = apply_mapping_rules(source_ir, bundle.rules)
    output_xml = ir_to_dublin_core_xml(target_ir)

    assert "oai_dc:dc" in output_xml
    assert isinstance(report.applied_rule_ids, list)
