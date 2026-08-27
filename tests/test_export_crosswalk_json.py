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


def test_derive_display_name_strips_trailing_parenthetical() -> None:
    display_name = MODULE.derive_display_name(
        {'mapping_set_description': 'DataCite 4.4 to Dublin Core Terms (DataCite -> Dublin Core Terms)'},
        'DataCite Metadata Schema',
        'Dublin Core Terms',
    )
    assert display_name == 'DataCite 4.4 to Dublin Core Terms'


@pytest.mark.parametrize(
    ('description', 'expected'),
    [
        (
            'abcd-access-biological_TO_darwin-core (ABCD (Access to Biological Collection Data) -> Darwin Core)',
            ('ABCD', 'Access to Biological Collection Data', 'Darwin Core', ''),
        ),
        (
            'dublin-core_TO_marc-machine-readable (Dublin Core -> MARC (Machine-Readable Cataloging))',
            ('Dublin Core', '', 'MARC', 'Machine-Readable Cataloging'),
        ),
        (
            'DataCite 4.4 to Dublin Core Terms (DataCite -> Dublin Core Terms)',
            ('DataCite', '', 'Dublin Core Terms', ''),
        ),
        ('No parenthetical at all', ('', '', '', '')),
    ],
)
def test_parse_description_names_handles_nested_parenthetical(
    description: str,
    expected: tuple[str, str, str, str],
) -> None:
    assert MODULE.parse_description_names(description) == expected


def test_export_emits_display_name_for_every_crosswalk() -> None:
    data = _load_output()
    for crosswalk in data['crosswalks']:
        display_name = crosswalk.get('display_name')
        assert isinstance(display_name, str)
        assert display_name.strip(), crosswalk['id']


def test_export_emits_canonical_acronym_and_expansion_fields() -> None:
    data = _load_output()
    for crosswalk in data['crosswalks']:
        for key in ['source_acronym', 'source_expansion', 'target_acronym', 'target_expansion']:
            assert isinstance(crosswalk.get(key), str), crosswalk['id']

    rdamsc_c1 = next(item for item in data['crosswalks'] if item['id'] == 'rdamsc_c1')
    rdamsc_c11 = next(item for item in data['crosswalks'] if item['id'] == 'rdamsc_c11')
    datacite44_to_dcterms = next(item for item in data['crosswalks'] if item['id'] == 'datacite44_to_dcterms')

    assert rdamsc_c1['source_acronym'] == 'ABCD'
    assert rdamsc_c1['source_expansion'] == 'Access to Biological Collection Data'
    assert rdamsc_c1['target_acronym'] == 'Darwin Core'
    assert rdamsc_c1['target_expansion'] == ''

    assert rdamsc_c11['source_acronym'] == 'Dublin Core'
    assert rdamsc_c11['source_expansion'] == ''
    assert rdamsc_c11['target_acronym'] == 'MARC'
    assert rdamsc_c11['target_expansion'] == 'Machine-Readable Cataloging'

    assert datacite44_to_dcterms['source_acronym'] == 'DataCite'
    assert datacite44_to_dcterms['source_expansion'] == ''
    assert datacite44_to_dcterms['target_acronym'] == 'Dublin Core Terms'
    assert datacite44_to_dcterms['target_expansion'] == ''

    assert not any(
        crosswalk['source_acronym'].startswith(prefix) or crosswalk['target_acronym'].startswith(prefix)
        for crosswalk in data['crosswalks']
        for prefix in ('dst_', 'src_', 'rdamsc_c')
    )


def test_display_name_for_datacite44_to_dcterms_is_human_readable() -> None:
    data = _load_output()
    crosswalk = next(item for item in data['crosswalks'] if item['id'] == 'datacite44_to_dcterms')
    display_name = crosswalk['display_name']
    assert 'DataCite' in display_name
    assert 'Dublin Core' in display_name
    assert not display_name.endswith(')')


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


def test_crosswalks_are_naturally_sorted() -> None:
    data = _load_output()
    ids = [crosswalk['id'] for crosswalk in data['crosswalks']]
    assert ids == sorted(ids, key=MODULE.natural_sort_key)

    rdamsc_ids = [cid for cid in ids if cid.startswith('rdamsc_c')]
    assert rdamsc_ids == [
        'rdamsc_c1',
        'rdamsc_c3',
        'rdamsc_c5',
        'rdamsc_c11',
        'rdamsc_c13',
        'rdamsc_c14',
        'rdamsc_c18',
        'rdamsc_c19',
        'rdamsc_c20',
        'rdamsc_c21',
        'rdamsc_c22',
        'rdamsc_c23',
        'rdamsc_c24',
        'rdamsc_c26',
        'rdamsc_c27',
        'rdamsc_c28',
        'rdamsc_c29',
        'rdamsc_c30',
        'rdamsc_c32',
        'rdamsc_c33',
        'rdamsc_c34',
        'rdamsc_c35',
        'rdamsc_c36',
        'rdamsc_c37',
        'rdamsc_c38',
    ]
    assert MODULE.natural_sort_key('rdamsc_c11') > MODULE.natural_sort_key('rdamsc_c2')
    assert MODULE.natural_sort_key('rdamsc_c11') < MODULE.natural_sort_key('rdamsc_c12')


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


def _load_graph_output() -> dict[str, object]:
    path = ROOT / 'exports' / 'graph' / 'crosswalk_graph.json'
    return json.loads(path.read_text(encoding='utf-8'))


def test_committed_graph_edges_expose_canonical_crosswalk_names() -> None:
    graph = _load_graph_output()
    for edge in graph['edges']:
        metadata = edge['metadata']
        assert isinstance(metadata['crosswalk_name'], str)
        assert metadata['crosswalk_name']
        assert '_TO_' not in metadata['crosswalk_name']
        assert isinstance(metadata['crosswalk_expansion'], str)
        assert isinstance(metadata['crosswalk_slug'], str)
        assert edge['label'].startswith(metadata['crosswalk_name'])

    rdamsc_c1 = next(edge for edge in graph['edges'] if edge['metadata']['crosswalk_id'] == 'rdamsc_c1')
    rdamsc_c11 = next(edge for edge in graph['edges'] if edge['metadata']['crosswalk_id'] == 'rdamsc_c11')
    datacite44_to_dcterms = next(
        edge for edge in graph['edges'] if edge['metadata']['crosswalk_id'] == 'datacite44_to_dcterms'
    )

    assert rdamsc_c1['metadata']['crosswalk_name'] == 'ABCD → Darwin Core'
    assert rdamsc_c11['metadata']['crosswalk_name'] == 'Dublin Core → MARC'
    assert datacite44_to_dcterms['metadata']['crosswalk_name'] == 'DataCite → Dublin Core Terms'


def test_committed_graph_mirror_matches_export_graph() -> None:
    export_graph = (ROOT / 'exports' / 'graph' / 'crosswalk_graph.json').read_bytes()
    web_graph = (ROOT / 'web' / 'data' / 'graph' / 'crosswalk_graph.json').read_bytes()
    assert export_graph == web_graph
