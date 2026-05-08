import csv
import io
import json

import yaml

from m2s3om_graph.models.crosswalk import Crosswalk, MappingRecord


def export_crosswalk_json(crosswalk: Crosswalk, mappings: list[MappingRecord]) -> str:
    payload = {
        "crosswalk": crosswalk.model_dump(mode="json"),
        "mappings": [x.model_dump(mode="json") for x in mappings],
    }
    return json.dumps(payload, indent=2, ensure_ascii=True)


def export_crosswalk_yaml(crosswalk: Crosswalk, mappings: list[MappingRecord]) -> str:
    payload = {
        "crosswalk": crosswalk.model_dump(mode="json"),
        "mappings": [x.model_dump(mode="json") for x in mappings],
    }
    return yaml.safe_dump(payload, sort_keys=False)


def export_crosswalk_csv(mappings: list[MappingRecord]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "mapping_id",
            "source_element_id",
            "target_element_id",
            "confidence",
            "justification",
            "transformation_hint",
            "ambiguity_flag",
            "semantic_loss_flag",
            "status",
        ]
    )
    for mapping in mappings:
        writer.writerow(
            [
                mapping.id,
                mapping.source_element_id,
                mapping.target_element_id,
                mapping.confidence,
                mapping.justification,
                mapping.transformation_hint,
                mapping.ambiguity_flag,
                mapping.semantic_loss_flag,
                mapping.status.value,
            ]
        )
    return buffer.getvalue()
