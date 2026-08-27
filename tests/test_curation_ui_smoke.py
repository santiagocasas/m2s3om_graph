from __future__ import annotations

import re
from pathlib import Path


def _strip_js_comments(text: str) -> str:
    return re.sub(r'//.*$', '', text, flags=re.MULTILINE)


def test_curation_module_exists_with_expected_exports() -> None:
    text = Path('web/src/curation.js').read_text(encoding='utf-8')
    for export in [
        'export async function postSuggestRequest',
        'export function acceptCandidate',
        'export function rejectCandidate',
        'export function getAcceptedCandidates',
        'export function getRejectedCandidates',
        'export function getSuggestApiUrl',
        'export function getDecision',
    ]:
        assert export in text, f'missing export: {export}'


def test_curation_module_has_no_persistence_calls() -> None:
    text = _strip_js_comments(Path('web/src/curation.js').read_text(encoding='utf-8'))
    for needle in ['localStorage', 'sessionStorage', 'indexedDB', 'indxdb:', 'db.create', 'db.merge', 'db.update']:
        assert needle not in text, f'unexpected persistence call: {needle}'


def test_curation_module_does_not_import_surrealdb() -> None:
    text = Path('web/src/curation.js').read_text(encoding='utf-8')
    assert "from 'surrealdb'" not in text
    assert "from '@surrealdb/wasm'" not in text


def test_curation_uses_env_configurable_endpoint() -> None:
    text = Path('web/src/curation.js').read_text(encoding='utf-8')
    assert text.count('import.meta.env.VITE_SUGGEST_API_URL') == 1
    assert "'/suggest'" in text
    assert re.search(r'huggingface\.co|hf\.space|codebase\.helmholtz\.cloud/[^\s\'\"]*suggest', text) is None


def test_main_js_renders_suggest_button_conditionally() -> None:
    text = Path('web/src/main.js').read_text(encoding='utf-8')
    assert 'target_paths' in text
    assert 'class="suggest-btn"' in text
    assert "from './curation.js'" in text


def test_main_js_has_actions_column_header() -> None:
    html = Path('web/index.html').read_text(encoding='utf-8')
    text = Path('web/src/main.js').read_text(encoding='utf-8')
    assert '<th>Actions</th>' in html
    assert 'colspan="7"' in text


def test_no_persistence_calls_in_main_js() -> None:
    text = _strip_js_comments(Path('web/src/main.js').read_text(encoding='utf-8'))
    for needle in ['localStorage', 'sessionStorage']:
        assert needle not in text, f'unexpected persistence call: {needle}'


def test_curation_module_exports_tsv_builders() -> None:
    text = Path('web/src/curation.js').read_text(encoding='utf-8')
    assert 'export function buildAcceptedTsv' in text
    assert 'export function downloadAcceptedTsv' in text


def test_tsv_header_matches_spec() -> None:
    text = Path('web/src/curation.js').read_text(encoding='utf-8')
    assert 'source_standard\\tsource_field\\ttarget_path\\tmapping_type\\tconfidence\\tevidence\\tnotes' in text


def test_download_uses_correct_filename_and_mime() -> None:
    text = Path('web/src/curation.js').read_text(encoding='utf-8')
    assert "'accepted_candidates.tsv'" in text
    assert 'text/tab-separated-values' in text


def test_download_creates_and_revokes_object_url() -> None:
    text = Path('web/src/curation.js').read_text(encoding='utf-8')
    assert 'URL.createObjectURL' in text
    assert 'URL.revokeObjectURL' in text


def test_index_html_has_export_button() -> None:
    html = Path('web/index.html').read_text(encoding='utf-8')
    assert 'id="export-tsv-btn"' in html


def test_index_html_has_no_writeback_notice() -> None:
    html = Path('web/index.html').read_text(encoding='utf-8')
    assert 'Curation decisions live in this browser session only.' in html
    assert 'merge into authoritative SSSOM files manually' in html
    assert 'the explorer never writes back.' in html


def test_main_js_wires_export_button() -> None:
    text = Path('web/src/main.js').read_text(encoding='utf-8')
    assert "getElementById('export-tsv-btn')" in text
    assert 'downloadAcceptedTsv' in text
    assert 'updateExportButton' in text
    assert text.count('updateExportButton();') >= 2


def test_main_js_populate_select_prefers_display_name_then_standards_fallback() -> None:
    text = Path('web/src/main.js').read_text(encoding='utf-8')
    assert 'populateSelect(data.crosswalks, data.standards)' in text
    assert 'display_name' in text
    assert 'naturalKey' in text
    assert 'standardName' in text
    assert '→' in text


def test_curation_module_still_has_no_persistence() -> None:
    text = _strip_js_comments(Path('web/src/curation.js').read_text(encoding='utf-8'))
    for needle in ['localStorage', 'sessionStorage', 'indexedDB', 'indxdb:', 'db.create', 'db.merge', 'db.update']:
        assert needle not in text, f'unexpected persistence call: {needle}'


def test_main_js_has_suggest_mode_chooser() -> None:
    text = Path('web/src/main.js').read_text(encoding='utf-8')
    for token in ['suggest-mode-row', 'suggest-mode-llm', 'suggest-mode-manual']:
        assert token in text, f'missing: {token}'


def test_main_js_has_manual_form_fields() -> None:
    text = Path('web/src/main.js').read_text(encoding='utf-8')
    for token in [
        'manual-form-row',
        'manual-form-submit',
        'data-field="source_path"',
        'data-field="target_path"',
        'data-field="mapping_type"',
        'data-field="confidence"',
        'data-field="evidence"',
        'data-field="notes"',
    ]:
        assert token in text, f'missing: {token}'


def test_manual_submit_reuses_llm_render_path_without_network() -> None:
    text = Path('web/src/main.js').read_text(encoding='utf-8')
    start = text.index('manual-form-submit')
    slice_text = text[start : start + 4000]
    assert 'renderCandidateRows(' in slice_text, 'missing shared render path'
    assert 'postSuggestRequest(' not in slice_text, 'manual path must not call postSuggestRequest'
    assert 'fetch(' not in slice_text, 'manual path must not call fetch'


def test_curation_js_unchanged_manual_mode_reuses_shared_accept_path() -> None:
    text = Path('web/src/curation.js').read_text(encoding='utf-8')
    for token in [
        'export async function postSuggestRequest',
        'export function acceptCandidate',
        'export function buildAcceptedTsv',
        'export function downloadAcceptedTsv',
    ]:
        assert token in text, f'missing export: {token}'
    assert 'manual' not in text, 'curation.js must not add a manual branch'
