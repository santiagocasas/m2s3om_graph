"""Export committed SSSOM TSV crosswalks to web/public/data/crosswalk_graph.json.

Local build: python scripts/build_pages.py && python scripts/export_crosswalk_json.py && (cd web && npm ci && npm run build) && mkdir -p public/explorer/data && cp -r web/dist/. public/explorer/ && cp web/public/data/crosswalk_graph.json public/explorer/data/
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SSSOM_DIR = ROOT / "exports" / "sssom"
OUTPUT_PATH = ROOT / "web" / "public" / "data" / "crosswalk_graph.json"


def _payload_from_comment(comment: str) -> dict[str, object]:
    if not comment:
        return {}
    try:
        loaded = json.loads(comment)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _confidence_from_row(row: dict[str, str]) -> float:
    try:
        confidence = float(row.get("confidence", "0.8") or 0.8)
    except ValueError:
        confidence = 0.8
    return max(0.0, min(1.0, confidence))


def _paths_from_payload_or_label(
    payload: dict[str, object],
    row: dict[str, str],
    payload_key: str,
    label_key: str,
) -> list[str]:
    if payload_key in payload:
        value = payload.get(payload_key)
        if isinstance(value, list):
            return [str(item) for item in value if str(item).strip()]
        return []
    label = (row.get(label_key, "") or "").strip()
    return [part for part in label.split("|") if part]


def parse_sssom_metadata(path: Path) -> dict[str, object]:
    header_lines: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("#"):
            break
        header_lines.append(line[1:])
    return yaml.safe_load("\n".join(header_lines)) or {}


def _slugify(raw: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", raw.lower())


def infer_strategy(comment: dict[str, object]) -> str:
    mapping_type = str(comment.get("mapping_type", "direct")).lower()
    if mapping_type in {"conditional", "aggregation"}:
        return "llm"
    if mapping_type == "missing":
        return "fallback"
    return "deterministic"


def derive_standard_ids(metadata: dict[str, object], crosswalk_stem: str) -> tuple[str, str, str, str]:
    description = str(metadata.get("mapping_set_description", "") or "")
    mapping_set_id = str(metadata.get("mapping_set_id", "") or "")

    source_raw: str | None = None
    target_raw: str | None = None
    source_name: str | None = None
    target_name: str | None = None

    if "(" in description and ")" in description:
        before_paren, paren_part = description.rsplit("(", 1)
        description = before_paren.strip()
        paren_part = paren_part.rstrip(")")
        if "->" in paren_part:
            left, right = [part.strip() for part in paren_part.split("->", 1)]
            source_name, target_name = left or None, right or None

    if "to" in description.lower() and (source_name is None or target_name is None):
        match = re.split(r"\s+to\s+", description, maxsplit=1, flags=re.IGNORECASE)
        if len(match) == 2:
            source_name = source_name or match[0].strip() or None
            target_name = target_name or match[1].strip() or None

    if ":" in mapping_set_id:
        raw_tail = mapping_set_id.split(":", 1)[1]
        if "_to_" in raw_tail:
            source_raw, target_raw = raw_tail.split("_to_", 1)
        else:
            source_raw = raw_tail

    if source_raw is None or target_raw is None:
        if "_to_" in crosswalk_stem:
            source_raw, target_raw = crosswalk_stem.split("_to_", 1)
        else:
            source_raw = source_raw or f"src_{crosswalk_stem}"
            target_raw = target_raw or f"dst_{crosswalk_stem}"

    source_id = _slugify(source_raw)
    target_id = _slugify(target_raw)

    if source_name is None:
        source_name = source_raw.replace("_", " ").strip() or source_id
    if target_name is None:
        target_name = target_raw.replace("_", " ").strip() or target_id

    return source_id, source_name, target_id, target_name


def validate_id(raw_id: str) -> None:
    if re.search(r"[^a-zA-Z0-9_]", raw_id):
        raise ValueError(
            f"Invalid ID {raw_id!r}: contains chars outside [a-zA-Z0-9_]. SurrealQL record IDs would need backtick escaping. Rename the source or use a stable hash suffix, e.g. {raw_id.split('-')[0]}_{hashlib.md5(raw_id.encode(), usedforsecurity=False).hexdigest()[:8]}."
        )


def build_rule_record(row: dict[str, str], comment: dict[str, object]) -> dict[str, object]:
    source_paths = _paths_from_payload_or_label(comment, row, "source_paths", "subject_label")
    target_paths = _paths_from_payload_or_label(comment, row, "target_paths", "object_label")
    mapping_type = str(comment.get("mapping_type", row.get("mapping_type", "direct"))).upper()
    if mapping_type == "MISSING":
        target_paths = []

    record = {
        "record_id": row.get("record_id", "") or "",
        "subject_id": row.get("subject_id", "") or "",
        "object_id": row.get("object_id", "") or "",
        "mapping_justification": row.get("mapping_justification", "") or "",
        "source_paths": source_paths,
        "target_paths": target_paths,
        "source_display": " | ".join(source_paths),
        "target_display": " | ".join(target_paths) if target_paths else "",
        "mapping_type": mapping_type,
        "confidence": _confidence_from_row(row),
        "semantic_loss": bool(
            comment["semantic_loss"] if "semantic_loss" in comment else mapping_type == "MISSING"
        ),
        "ambiguity": bool(
            comment["ambiguity"]
            if "ambiguity" in comment
            else mapping_type in {"CONDITIONAL", "AGGREGATION"}
        ),
        "transform": comment.get("transform") if isinstance(comment.get("transform"), dict) else {},
        "notes": None if comment.get("notes") is None else str(comment.get("notes")),
        "strategy": infer_strategy({"mapping_type": mapping_type}),
        "evidence": {
            "subject_id": row.get("subject_id"),
            "object_id": row.get("object_id"),
            "record_id": row.get("record_id"),
            "mapping_justification": row.get("mapping_justification"),
        },
    }
    return record


def parse_sssom_rules(content: str) -> list[dict[str, object]]:
    rows = [line for line in content.splitlines() if line and not line.startswith("#")]
    if not rows:
        return []

    reader = csv.DictReader(io.StringIO("\n".join(rows)), delimiter="\t")
    out: list[dict[str, object]] = []

    for row in reader:
        comment = _payload_from_comment(row.get("comment", "") or "")
        out.append(build_rule_record(row, comment))

    return out


def export_crosswalk_json(
    sssom_dir: Path | None = None,
    output_path: Path | None = None,
) -> Path:
    sssom_dir = sssom_dir or SSSOM_DIR
    output_path = output_path or OUTPUT_PATH

    standards_map: dict[str, dict[str, str]] = {}
    crosswalks: list[dict[str, object]] = []
    validation_errors: list[str] = []

    for tsv_path in sorted(sssom_dir.glob("*.sssom.tsv")):
        crosswalk_stem = tsv_path.stem.replace(".sssom", "")
        metadata = parse_sssom_metadata(tsv_path)
        source_id, source_name, target_id, target_name = derive_standard_ids(metadata, crosswalk_stem)

        for candidate in (crosswalk_stem, source_id, target_id):
            try:
                validate_id(candidate)
            except ValueError as exc:
                validation_errors.append(str(exc))

        for standard_id, standard_name in ((source_id, source_name), (target_id, target_name)):
            existing = standards_map.get(standard_id)
            if existing is None:
                standards_map[standard_id] = {"id": standard_id, "name": standard_name}
            elif existing.get("name") != standard_name and standard_name:
                print(
                    f"WARNING: standard {standard_id!r} has conflicting names {existing.get('name')!r} and {standard_name!r}; keeping the first non-empty name",
                    file=sys.stderr,
                )
                if not existing.get("name"):
                    existing["name"] = standard_name

        rules = parse_sssom_rules(tsv_path.read_text(encoding="utf-8"))
        crosswalks.append(
            {
                "id": crosswalk_stem,
                "source": source_id,
                "target": target_id,
                "rules": sorted(
                    rules,
                    key=lambda rule: str(rule.get("record_id") or rule.get("subject_id") or ""),
                ),
            }
        )

    if validation_errors:
        raise ValueError("; ".join(validation_errors))

    output = {
        "standards": sorted(standards_map.values(), key=lambda item: item["id"]),
        "crosswalks": sorted(crosswalks, key=lambda item: item["id"]),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    print(export_crosswalk_json())
