from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'export_crosswalk_json', ROOT / 'scripts' / 'export_crosswalk_json.py'
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _load_output() -> dict[str, object]:
    path = MODULE.export_crosswalk_json()
    return json.loads(path.read_text(encoding='utf-8'))


def test_export_produces_expected_top_level_shape() -> None:
    data = _load_output()
    assert isinstance(data['standards'], list)
    assert isinstance(data['crosswalks'], list)


def test_export_all_rules_have_strategy_inferred_from_mapping_type() -> None:
    assert MODULE.infer_strategy({'mapping_type': 'conditional'}) == 'llm'
    assert MODULE.infer_strategy({'mapping_type': 'aggregation'}) == 'llm'
    assert MODULE.infer_strategy({'mapping_type': 'missing'}) == 'fallback'
    assert MODULE.infer_strategy({'mapping_type': 'direct'}) == 'deterministic'
    assert MODULE.infer_strategy({}) == 'deterministic'

    data = _load_output()
    for crosswalk in data['crosswalks']:
        for rule in crosswalk['rules']:
            expected = MODULE.infer_strategy({'mapping_type': str(rule['mapping_type']).lower()})
            assert rule['strategy'] == expected


def test_export_rejects_crosswalk_id_with_dashes_at_build_time(tmp_path: Path) -> None:
    fake = tmp_path / 'fake-crosswalk.sssom.tsv'
    fake.write_text(
        '#mapping_set_id: m2s3om_graph:fake-crosswalk\n'
        '#mapping_set_description: Fake Crosswalk (Fake -> Crosswalk)\n'
        'record_id\tsubject_id\tsubject_label\tpredicate_id\tobject_id\tobject_label\tmapping_justification\tconfidence\tcomment\n'
        'mapping_rule:1\tsrc:1\tSource\tskos:exactMatch\tdst:1\tTarget\tsemapv:ManualMappingCuration\t0.9\t{"mapping_type": "direct", "source_paths": ["Source"], "target_paths": ["Target"]}\n',
        encoding='utf-8',
    )

    with pytest.raises(ValueError) as excinfo:
        MODULE.export_crosswalk_json(sssom_dir=tmp_path, output_path=tmp_path / 'out.json')

    message = str(excinfo.value)
    assert 'fake-crosswalk' in message
    assert 'hash' in message.lower() or 'backtick' in message.lower()


def test_export_standards_derived_from_sssom_headers_not_filenames() -> None:
    data = _load_output()
    crosswalk = next(item for item in data['crosswalks'] if item['id'] == 'datacite44_to_dcterms')
    source = next(item for item in data['standards'] if item['id'] == crosswalk['source'])
    target = next(item for item in data['standards'] if item['id'] == crosswalk['target'])
    assert 'DataCite' in source['name']
    assert 'Dublin Core' in target['name']


def test_missing_rules_preserved_with_semantic_loss() -> None:
    data = _load_output()
    missing = [
        rule
        for crosswalk in data['crosswalks']
        for rule in crosswalk['rules']
        if rule['mapping_type'] == 'MISSING'
    ]
    assert missing
    for rule in missing:
        assert rule['semantic_loss'] is True
        assert rule['target_paths'] == []


def test_rule_display_strings_join_arrays_with_pipe() -> None:
    data = _load_output()
    for crosswalk in data['crosswalks']:
        for rule in crosswalk['rules']:
            assert rule['source_display'] == ' | '.join(rule['source_paths'])
            assert rule['target_display'] == ' | '.join(rule['target_paths'])


def test_export_is_deterministic_across_runs(tmp_path: Path) -> None:
    first = MODULE.export_crosswalk_json(output_path=tmp_path / 'first.json')
    second = MODULE.export_crosswalk_json(output_path=tmp_path / 'second.json')
    assert first.read_bytes() == second.read_bytes()
