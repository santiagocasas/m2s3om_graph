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
    assert 'http://localhost:8000/suggest' in text
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
