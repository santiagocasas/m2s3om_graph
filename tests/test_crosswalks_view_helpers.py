from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))

from views import crosswalks
from m2s3om_graph.db import CrosswalkRecord, InMemoryCrosswalkStore


def _store_with_crosswalks() -> tuple[
    InMemoryCrosswalkStore,
    CrosswalkRecord,
    CrosswalkRecord,
]:
    store = InMemoryCrosswalkStore()
    first = store.upsert_crosswalk(
        CrosswalkRecord(
            id="rdamsc_c1",
            name="One",
            source_standard_id="s1",
            target_standard_id="t1",
            msc_id="msc:c1",
        )
    )
    second = store.upsert_crosswalk(
        CrosswalkRecord(
            id="rdamsc_c2",
            name="Two",
            source_standard_id="s1",
            target_standard_id="t1",
            msc_id="msc:c2",
        )
    )
    return store, first, second


def test_status_counts_uses_persisted_failure_and_missing_defaults(
    tmp_path: Path,
) -> None:
    store, first, second = _store_with_crosswalks()
    counts = crosswalks._status_counts(
        store,
        tmp_path,
        [first, second],
        {
            first.id: {
                "status": "failed_unreachable",
                "result": {"ok": False, "reason": "artifacts_unreachable"},
            }
        },
    )
    assert counts["failed_unreachable"] == 1
    assert counts["missing_sssom"] == 1


def test_ingest_selected_contract_boundaries(tmp_path: Path, monkeypatch) -> None:
    store, first, _ = _store_with_crosswalks()

    monkeypatch.setattr(
        crosswalks,
        "run_bootstrap_pipeline",
        lambda *_args, **_kwargs: {"processed": []},
    )
    empty_result = crosswalks._ingest_selected(store, tmp_path, first)
    assert empty_result["ok"] is False
    assert empty_result["reason"] == "not_processed"

    monkeypatch.setattr(
        crosswalks,
        "run_bootstrap_pipeline",
        lambda *_args, **_kwargs: {"processed": [{"result": "invalid"}]},
    )
    invalid_result = crosswalks._ingest_selected(store, tmp_path, first)
    assert invalid_result["ok"] is False
    assert invalid_result["reason"] == "invalid_pipeline_result"

    expected = {"ok": True, "crosswalk_id": first.id, "total_rules": 5}
    monkeypatch.setattr(
        crosswalks,
        "run_bootstrap_pipeline",
        lambda *_args, **_kwargs: {"processed": [{"result": expected}]},
    )
    success = crosswalks._ingest_selected(store, tmp_path, first)
    assert success == expected
