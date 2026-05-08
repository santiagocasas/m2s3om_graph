from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.state import _auto_sync_enabled, _seed_store_from_sssom_exports
from m2s3om_graph.db import (
    CrosswalkBundle,
    CrosswalkRecord,
    InMemoryCrosswalkStore,
    MappingRuleRecord,
    MappingType,
    StandardRecord,
)
from m2s3om_graph.sssom import write_bundle_sssom


def test_auto_sync_disabled_by_default(monkeypatch) -> None:
    monkeypatch.delenv("M2S3OM_AUTO_SYNC_ON_START", raising=False)
    assert _auto_sync_enabled() is False


def test_auto_sync_enabled_by_env(monkeypatch) -> None:
    monkeypatch.setenv("M2S3OM_AUTO_SYNC_ON_START", "1")
    assert _auto_sync_enabled() is True


def test_seed_store_from_sssom_exports(tmp_path: Path) -> None:
    bundle = CrosswalkBundle(
        crosswalk=CrosswalkRecord(
            id="rdamsc_c999",
            name="Demo Mapping",
            source_standard_id="demo_source",
            target_standard_id="demo_target",
            version="1.0",
            msc_id="msc:c999",
            doc_uri="https://example.org/mapping",
        ),
        source_standard=StandardRecord(id="demo_source", name="Demo Source"),
        target_standard=StandardRecord(id="demo_target", name="Demo Target"),
        rules=[
            MappingRuleRecord(
                id="mapping_rule:1",
                crosswalk_id="rdamsc_c999",
                source_paths=["demo:title"],
                target_paths=["demo:name"],
                mapping_type=MappingType.DIRECT,
                confidence=0.9,
                transform={"op": "copy"},
            )
        ],
    )
    write_bundle_sssom(bundle, tmp_path / "rdamsc_c999.sssom.tsv")

    store = InMemoryCrosswalkStore()
    seeded_rules = _seed_store_from_sssom_exports(store, tmp_path)

    assert seeded_rules == 1
    crosswalks = store.list_crosswalks()
    assert len(crosswalks) == 1
    assert crosswalks[0].name == "Demo Mapping"
    assert crosswalks[0].msc_id == "msc:c999"
    assert {standard.name for standard in store.list_standards()} == {
        "Demo Source",
        "Demo Target",
    }
    bundle_loaded = store.get_crosswalk_bundle("rdamsc_c999")
    assert bundle_loaded is not None
    assert len(bundle_loaded.rules) == 1
