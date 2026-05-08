import csv
import io
import json
import re
from pathlib import Path
from typing import cast

import yaml

from m2s3om_graph.atomic_files import atomic_write_text
from m2s3om_graph.db import (
    CrosswalkBundle,
    MappingRuleRecord,
    MappingType,
    stable_id,
)

_NON_WORD_RE = re.compile(r"[^a-z0-9]+")

SKOS_NS_URL = "http://www.w3.org/2004/02/skos/core#"
SEMAPV_NS_URL = "https://w3id.org/semapv/vocab/"
CC_BY_40_LICENSE_URL = "https://creativecommons.org/licenses/by/4.0/"
M2S3OM_LOCAL_BASE_URL = "https://m2s3om_graph.local"


def _m2s3om_graph_standard_iri(standard_id: str) -> str:
    return f"{M2S3OM_LOCAL_BASE_URL.rstrip('/')}/{standard_id}/"


def _slug(value: str) -> str:
    lowered = value.strip().lower()
    cleaned = _NON_WORD_RE.sub("_", lowered).strip("_")
    return cleaned or "term"


def _predicate_for_rule(rule: MappingRuleRecord) -> str:
    if rule.mapping_type == MappingType.DIRECT:
        return "skos:exactMatch"
    if rule.mapping_type == MappingType.MISSING:
        return "skos:relatedMatch"
    if rule.mapping_type == MappingType.CONDITIONAL:
        return "skos:relatedMatch"
    if rule.mapping_type == MappingType.AGGREGATION:
        return "skos:broadMatch"
    if rule.mapping_type == MappingType.DECOMPOSITION:
        return "skos:narrowMatch"
    return "skos:relatedMatch"


def _justification_for_rule(rule: MappingRuleRecord) -> str:
    if rule.ambiguity:
        return "semapv:CompositeMatching"
    return "semapv:ManualMappingCuration"


def bundle_to_sssom_tsv(bundle: CrosswalkBundle) -> str:
    metadata = {
        "mapping_set_id": f"m2s3om_graph:{bundle.crosswalk.id}",
        "mapping_set_version": bundle.crosswalk.version or "unknown",
        "mapping_set_description": (
            f"{bundle.crosswalk.name}"
            f" ({bundle.source_standard.name} -> {bundle.target_standard.name})"
        ),
        "curie_map": {
            "src": _m2s3om_graph_standard_iri(bundle.source_standard.id),
            "dst": _m2s3om_graph_standard_iri(bundle.target_standard.id),
            "skos": SKOS_NS_URL,
            "semapv": SEMAPV_NS_URL,
        },
        "license": CC_BY_40_LICENSE_URL,
    }
    if bundle.crosswalk.doc_uri:
        metadata["mapping_set_source"] = bundle.crosswalk.doc_uri

    lines: list[str] = []
    metadata_yaml = yaml.safe_dump(metadata, sort_keys=False).splitlines()
    for line in metadata_yaml:
        lines.append(f"#{line}")

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter="\t", lineterminator="\n")
    writer.writerow(
        [
            "record_id",
            "subject_id",
            "subject_label",
            "predicate_id",
            "object_id",
            "object_label",
            "mapping_justification",
            "confidence",
            "comment",
        ]
    )

    for rule in bundle.rules:
        source_paths = rule.source_paths or ["unknown_source"]
        target_paths = rule.target_paths
        subject_label = "|".join(source_paths)
        object_label = "|".join(target_paths)
        subject_id = f"src:{_slug(source_paths[0])}"
        object_id = f"dst:{_slug(target_paths[0])}" if target_paths else ""
        payload = {
            "mapping_type": rule.mapping_type.value,
            "source_paths": source_paths,
            "target_paths": target_paths,
            "transform": rule.transform,
            "semantic_loss": rule.semantic_loss,
            "ambiguity": rule.ambiguity,
            "notes": rule.notes,
        }
        writer.writerow(
            [
                rule.id,
                subject_id,
                subject_label,
                _predicate_for_rule(rule),
                object_id,
                object_label,
                _justification_for_rule(rule),
                f"{rule.confidence:.3f}",
                json.dumps(payload, ensure_ascii=True),
            ]
        )

    lines.extend(buffer.getvalue().splitlines())
    return "\n".join(lines) + "\n"


def write_bundle_sssom(bundle: CrosswalkBundle, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(output_path, bundle_to_sssom_tsv(bundle))
    return output_path


def _payload_from_comment(comment: str) -> dict[str, object]:
    if not comment:
        return {}
    try:
        loaded = json.loads(comment)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _mapping_type_from_payload(payload: dict[str, object]) -> MappingType:
    raw_mapping_type = str(payload.get("mapping_type", "direct"))
    try:
        return MappingType(raw_mapping_type)
    except ValueError:
        return MappingType.DIRECT


def _paths_from_payload_or_label(
    payload: dict[str, object],
    row: dict[str, str],
    payload_key: str,
    label_key: str,
) -> list[object]:
    if payload_key in payload:
        value = payload.get(payload_key)
        return value if isinstance(value, list) else []
    label = row.get(label_key, "") or ""
    return [x for x in label.split("|") if x]


def _transform_from_payload(payload: dict[str, object]) -> dict[str, object]:
    transform_obj = payload.get("transform")
    if not isinstance(transform_obj, dict):
        transform_obj = {"op": cast(object, "copy")}
    return {str(k): v for k, v in transform_obj.items()}


def _rule_id_from_row(
    row: dict[str, str],
    crosswalk_id: str,
    source_paths: list[object],
    target_paths: list[object],
) -> str:
    raw_id = row.get("record_id") or ""
    trimmed = raw_id.strip()
    if trimmed:
        return trimmed
    return stable_id(
        "mapping_rule",
        crosswalk_id,
        "|".join(str(x) for x in source_paths),
        "|".join(str(x) for x in target_paths),
    )


def _confidence_from_row(row: dict[str, str]) -> float:
    try:
        confidence = float(row.get("confidence", "0.8") or 0.8)
    except ValueError:
        confidence = 0.8
    return max(0.0, min(1.0, confidence))


def _semantic_loss_from_payload(
    payload: dict[str, object],
    mapping_type: MappingType,
) -> bool:
    if "semantic_loss" not in payload:
        return mapping_type == MappingType.MISSING
    return bool(payload.get("semantic_loss"))


def _ambiguity_from_payload(
    payload: dict[str, object],
    mapping_type: MappingType,
) -> bool:
    if "ambiguity" not in payload:
        return mapping_type in {MappingType.CONDITIONAL, MappingType.AGGREGATION}
    return bool(payload.get("ambiguity"))


def _notes_from_payload(payload: dict[str, object]) -> str | None:
    notes = payload.get("notes")
    if notes is None:
        return None
    return str(notes)


def sssom_tsv_to_rules(content: str, crosswalk_id: str) -> list[MappingRuleRecord]:
    rows = [line for line in content.splitlines() if line and not line.startswith("#")]
    if not rows:
        return []

    reader = csv.DictReader(io.StringIO("\n".join(rows)), delimiter="\t")
    out: list[MappingRuleRecord] = []

    for row in reader:
        comment = row.get("comment", "") or ""
        payload = _payload_from_comment(comment)
        mapping_type = _mapping_type_from_payload(payload)
        source_paths = _paths_from_payload_or_label(
            payload,
            row,
            "source_paths",
            "subject_label",
        )
        target_paths = _paths_from_payload_or_label(
            payload,
            row,
            "target_paths",
            "object_label",
        )
        transform = _transform_from_payload(payload)
        rule_id = _rule_id_from_row(row, crosswalk_id, source_paths, target_paths)
        confidence = _confidence_from_row(row)
        semantic_loss = _semantic_loss_from_payload(payload, mapping_type)
        ambiguity = _ambiguity_from_payload(payload, mapping_type)
        notes = _notes_from_payload(payload)

        out.append(
            MappingRuleRecord(
                id=rule_id,
                crosswalk_id=crosswalk_id,
                source_paths=[str(x) for x in source_paths if str(x).strip()],
                target_paths=[str(x) for x in target_paths if str(x).strip()],
                mapping_type=mapping_type,
                confidence=confidence,
                semantic_loss=semantic_loss,
                ambiguity=ambiguity,
                transform=transform,
                notes=notes,
            )
        )

    return out


def load_sssom_rules(path: Path, crosswalk_id: str) -> list[MappingRuleRecord]:
    if not path.exists():
        return []
    content = path.read_text(encoding="utf-8")
    return sssom_tsv_to_rules(content, crosswalk_id)
