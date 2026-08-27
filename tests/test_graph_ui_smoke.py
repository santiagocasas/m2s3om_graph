from __future__ import annotations

import json
from pathlib import Path


def test_graph_adapter_supports_checked_in_flat_export() -> None:
    text = Path('web/src/graph.js').read_text(encoding='utf-8')
    assert 'const attrs = n.attributes || n;' in text
    assert "const kind = attrs.kind || attrs.type || 'standard';" in text
    assert 'const metadata = e.metadata || {};' in text
    assert '...metadata,' in text


def test_checked_in_graph_has_canonical_standard_labels() -> None:
    data = json.loads(Path('web/data/graph/crosswalk_graph.json').read_text(encoding='utf-8'))
    labels = {node['id']: node['label'] for node in data['nodes']}
    assert labels['rdamsc_m1'].startswith('ABCD')
    assert labels['rdamsc_m9'] == 'Darwin Core'


def test_non_explorer_routes_remove_crosswalk_headings() -> None:
    text = Path('web/src/main.js').read_text(encoding='utf-8')
    assert text.count('currentCrosswalkTitleEl?.remove();') == 2
    assert text.count('currentCrosswalkSubtitleEl?.remove();') == 2
