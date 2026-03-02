from kaigraph.mapping.exporters import (
    export_crosswalk_csv,
    export_crosswalk_json,
    export_crosswalk_yaml,
)
from kaigraph.models import Crosswalk, MappingRecord


def test_exporters() -> None:
    crosswalk = Crosswalk(
        id="crosswalk:a:b", source_standard_id="a", target_standard_id="b"
    )
    mappings = [
        MappingRecord(
            id="mapping:1",
            crosswalk_id=crosswalk.id,
            source_element_id="a:title",
            target_element_id="b:name",
            confidence=0.85,
            justification="lexical match",
            transformation_hint="direct mapping",
        )
    ]
    as_json = export_crosswalk_json(crosswalk, mappings)
    as_yaml = export_crosswalk_yaml(crosswalk, mappings)
    as_csv = export_crosswalk_csv(mappings)
    assert "crosswalk" in as_json
    assert "mappings:" in as_yaml
    assert "mapping_id" in as_csv
