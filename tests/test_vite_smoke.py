from __future__ import annotations

from pathlib import Path


def test_vite_dist_index_html_exists_after_build() -> None:
    dist = Path('web/dist/index.html')
    if not dist.exists():
        import pytest

        pytest.skip('run `cd web && npm run build` first')
    assert dist.exists()


def test_explorer_main_uses_array_target_paths() -> None:
    text = Path('web/src/main.js').read_text(encoding='utf-8')
    assert 'target_paths' in text
    assert 'source_paths' in text or 'source_display' in text


def test_explorer_has_fail_closed_copy() -> None:
    text = Path('web/src/main.js').read_text(encoding='utf-8')
    assert 'Data unavailable: failed to load crosswalk_graph.json' in text


def test_explorer_has_semantic_loss_aria_label() -> None:
    text = Path('web/src/main.js').read_text(encoding='utf-8')
    assert 'aria-label="semantic loss detected"' in text
