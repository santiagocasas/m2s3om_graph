"""Export committed SSSOM TSV crosswalks to public/data/crosswalk_graph.json.

Local build: python scripts/build_pages.py && python scripts/export_crosswalk_json.py && (cd web && npm ci && npm run build) && mkdir -p public/explorer/data && cp -r web/dist/. public/explorer/ && cp public/data/crosswalk_graph.json public/explorer/data/
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SSSOM_DIR = ROOT / 'exports' / 'sssom'
OUTPUT_PATH = ROOT / 'public' / 'data' / 'crosswalk_graph.json'


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
        confidence = float(row.get('confidence', '0.8') or 0.8)
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
            return [str(x) for x in value if str(x).strip()]
        return []
    label = (row.get(label_key, '') or '').strip()
    return [part for part in label.split('|') if part]


def _read_metadata(tsv_path: Path) -> dict[str, object]:
    header_lines: list[str] = []
    for line in tsv_path.read_text(encoding='utf-8').splitlines():
        if not line.startswith('#'):
            break
        header_lines.append(line[1:])
    return yaml.safe_load('\n'.join(header_lines)) or {}


def _validate_stem(stem: str) -> None:
    if not all(ch.isalnum() or ch == '_' for ch in stem):
        raise ValueError(
            f"Invalid crosswalk ID {stem!r}: use only [a-zA-Z0-9_] characters. "
            'Rename the source or use a stable underscored stem.'
        )


def _rules_from_file(tsv_path: Path) -> list[dict[str, object]]:
    lines = [line for line in tsv_path.read_text(encoding='utf-8').splitlines() if line and not line.startswith('#')]
    reader = csv.DictReader(io.StringIO('\n'.join(lines)), delimiter='\t')
    out: list[dict[str, object]] = []
    for row in reader:
        payload = _payload_from_comment(row.get('comment', '') or '')
        source_paths = _paths_from_payload_or_label(payload, row, 'source_paths', 'subject_label')
        target_paths = _paths_from_payload_or_label(payload, row, 'target_paths', 'object_label')
        mapping_type = str(payload.get('mapping_type', 'direct')).upper()
        source_path = source_paths[0] if source_paths else ''
        target_path = target_paths[0] if target_paths else ''
        out.append(
            {
                'record_id': row.get('record_id', ''),
                'source_paths': source_paths,
                'target_paths': target_paths,
                'source_path': source_path,
                'target_path': target_path,
                'mapping_type': mapping_type,
                'confidence': _confidence_from_row(row),
                'semantic_loss': bool(payload.get('semantic_loss', False)),
                'ambiguity': bool(payload.get('ambiguity', False)),
                'strategy': 'deterministic',
                'evidence': payload.get('notes') or '',
            }
        )
    return out


def export_crosswalk_json() -> Path:
    standards: dict[str, dict[str, str]] = {}
    crosswalks: list[dict[str, object]] = []

    for tsv_path in sorted(SSSOM_DIR.glob('*.sssom.tsv')):
        stem = tsv_path.stem.replace('.sssom', '')
        _validate_stem(stem)
        metadata = _read_metadata(tsv_path)
        source_id, target_id = stem.split('_to_', 1) if '_to_' in stem else (f'src_{stem}', f'dst_{stem}')
        standards.setdefault(source_id, {'id': source_id, 'name': source_id})
        standards.setdefault(target_id, {'id': target_id, 'name': target_id})
        rules = _rules_from_file(tsv_path)
        crosswalks.append(
            {
                'id': stem,
                'source': source_id,
                'target': target_id,
                'rules': rules,
                'metadata': metadata,
            }
        )

    output = {
        'standards': sorted(standards.values(), key=lambda item: item['id']),
        'crosswalks': sorted(crosswalks, key=lambda item: item['id']),
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding='utf-8')
    return OUTPUT_PATH


if __name__ == '__main__':
    print(export_crosswalk_json())
