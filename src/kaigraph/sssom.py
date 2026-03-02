import csv
import io
import json
import re
from pathlib import Path
from typing import cast

import yaml

from kaigraph.db import (
    CrosswalkBundle,
    MappingRuleRecord,
    MappingType,
    stable_id,
)

_NON_WORD_RE = re.compile(r"[^a-z0-9]+")


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
    if rule.mapping_type == MappingType.MISSING:
        return "semapv:ManualMappingCuration"
    return "semapv:ManualMappingCuration"


def bundle_to_sssom_tsv(bundle: CrosswalkBundle) -> str:
    metadata = {
        "mapping_set_id": f"kaigraph:{bundle.crosswalk.id}",
        "mapping_set_version": bundle.crosswalk.version or "unknown",
        "mapping_set_description": (
            f"{bundle.crosswalk.name}"
            f" ({bundle.source_standard.name} -> {bundle.target_standard.name})"
        ),
        "curie_map": {
            "src": f"https://kaigraph.local/{bundle.source_standard.id}/",
            "dst": f"https://kaigraph.local/{bundle.target_standard.id}/",
            "skos": "http://www.w3.org/2004/02/skos/core#",
            "semapv": "https://w3id.org/semapv/vocab/",
        },
        "license": "https://creativecommons.org/licenses/by/4.0/",
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
    output_path.write_text(bundle_to_sssom_tsv(bundle), encoding="utf-8")
    return output_path


def sssom_tsv_to_rules(content: str, crosswalk_id: str) -> list[MappingRuleRecord]:
    rows = [line for line in content.splitlines() if line and not line.startswith("#")]
    if not rows:
        return []

    reader = csv.DictReader(io.StringIO("\n".join(rows)), delimiter="\t")
    out: list[MappingRuleRecord] = []

    for row in reader:
        comment = row.get("comment", "") or ""
        payload: dict[str, object] = {}
        if comment:
            try:
                loaded = json.loads(comment)
                if isinstance(loaded, dict):
                    payload = loaded
            except json.JSONDecodeError:
                payload = {}

        raw_mapping_type = str(payload.get("mapping_type", "direct"))
        try:
            mapping_type = MappingType(raw_mapping_type)
        except ValueError:
            mapping_type = MappingType.DIRECT

        source_paths = payload.get("source_paths")
        if not isinstance(source_paths, list):
            source_label = row.get("subject_label", "") or ""
            source_paths = [x for x in source_label.split("|") if x]

        target_paths = payload.get("target_paths")
        if not isinstance(target_paths, list):
            object_label = row.get("object_label", "") or ""
            target_paths = [x for x in object_label.split("|") if x]

        transform_obj = payload.get("transform")
        transform: dict[str, object]
        if isinstance(transform_obj, dict):
            transform = {str(k): v for k, v in transform_obj.items()}
        else:
            transform = {"op": cast(object, "copy")}

        raw_id = row.get("record_id") or ""
        rule_id = raw_id.strip() or stable_id(
            "mapping_rule",
            crosswalk_id,
            "|".join(str(x) for x in source_paths),
            "|".join(str(x) for x in target_paths),
        )

        try:
            confidence = float(row.get("confidence", "0.8") or 0.8)
        except ValueError:
            confidence = 0.8
        confidence = max(0.0, min(1.0, confidence))

        semantic_loss = bool(
            payload.get("semantic_loss", mapping_type == MappingType.MISSING)
        )
        ambiguity = bool(
            payload.get(
                "ambiguity",
                mapping_type in {MappingType.CONDITIONAL, MappingType.AGGREGATION},
            )
        )
        notes = payload.get("notes")
        if notes is not None:
            notes = str(notes)

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
