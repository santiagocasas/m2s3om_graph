from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'export_crosswalk_json', ROOT / 'scripts' / 'export_crosswalk_json.py'
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_export_produces_expected_top_level_shape() -> None:
    path = MODULE.export_crosswalk_json()
    data = __import__('json').loads(path.read_text(encoding='utf-8'))
    assert isinstance(data['standards'], list)
    assert isinstance(data['crosswalks'], list)


@pytest.mark.xfail(reason='filled by plan 02: rich audit fields')
def test_export_all_rules_have_strategy_inferred_from_mapping_type() -> None:
    raise NotImplementedError


@pytest.mark.xfail(reason='filled by plan 02: rich audit fields')
def test_export_rejects_crosswalk_id_with_dashes_at_build_time() -> None:
    raise NotImplementedError


@pytest.mark.xfail(reason='filled by plan 02: rich audit fields')
def test_export_standards_derived_from_sssom_headers_not_filenames() -> None:
    raise NotImplementedError
