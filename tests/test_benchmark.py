from pathlib import Path

from kaigraph.benchmark.runner import run_fixture_benchmark
from kaigraph.db import InMemoryCrosswalkStore
from kaigraph.ingest.crosswalk_ingestion import ingest_datacite_to_dc_pdf


def test_fixture_benchmark_runs(datacite_mapping_pdf_path: Path) -> None:
    store = InMemoryCrosswalkStore()
    crosswalk_id = ingest_datacite_to_dc_pdf(store, datacite_mapping_pdf_path)
    bundle = store.get_crosswalk_bundle(crosswalk_id)
    assert bundle is not None

    source_xml = """
<oaire:resource xmlns:oaire="http://namespace.openaire.eu/schema/oaire/" xmlns:datacite="http://datacite.org/schema/kernel-4">
  <datacite:titles><datacite:title>Example title</datacite:title></datacite:titles>
  <datacite:creators><datacite:creator><datacite:creatorName>Example, Alice</datacite:creatorName></datacite:creator></datacite:creators>
  <datacite:identifier>10.1234/example</datacite:identifier>
</oaire:resource>
"""
    expected_text = """
title: Example title
creator: Example, Alice
identifier: 10.1234/example
"""
    summary = run_fixture_benchmark(bundle, source_xml, expected_text, n_cases=3)
    assert len(summary.cases) == 3
    assert 0.0 <= summary.avg_field_coverage <= 1.0
