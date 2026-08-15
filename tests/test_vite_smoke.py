from __future__ import annotations

from pathlib import Path

import pytest


def test_vite_dist_index_html_exists_after_build() -> None:
    dist = Path('web/dist/index.html')
    if not dist.exists():
        pytest.skip('run `cd web && npm run build` first')
    assert dist.exists()


@pytest.mark.xfail(reason='filled by plan 03: rendered rules table asserts')
def test_explorer_main_uses_array_target_paths() -> None:
    raise NotImplementedError
