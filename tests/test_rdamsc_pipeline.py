from pathlib import Path
from typing import cast

from kaigraph.db import CrosswalkRecord, InMemoryCrosswalkStore
from kaigraph.rdamsc.pipeline import (
    load_pipeline_status,
    resolve_crosswalk_status,
    run_bootstrap_pipeline,
    status_from_result,
)


def test_pipeline_continues_when_one_mapping_raises(
    monkeypatch, tmp_path: Path
) -> None:
    store = InMemoryCrosswalkStore()
    _ = store.upsert_crosswalk(
        CrosswalkRecord(
            id="rdamsc_c1",
            name="One",
            source_standard_id="s1",
            target_standard_id="t1",
            msc_id="msc:c1",
        )
    )
    _ = store.upsert_crosswalk(
        CrosswalkRecord(
            id="rdamsc_c2",
            name="Two",
            source_standard_id="s1",
            target_standard_id="t1",
            msc_id="msc:c2",
        )
    )

    monkeypatch.setattr("kaigraph.rdamsc.pipeline.sync_rdamsc_catalog", lambda *_: 2)
    monkeypatch.setattr(
        "kaigraph.rdamsc.pipeline.pipeline_status_path",
        lambda: tmp_path / "rdamsc_pipeline_status.json",
    )

    def fake_ingest(*args, **kwargs):
        crosswalk_id = cast(str, args[1])
        if crosswalk_id == "rdamsc_c1":
            raise RuntimeError("boom")
        return {"ok": True, "crosswalk_id": crosswalk_id, "total_rules": 3}

    monkeypatch.setattr(
        "kaigraph.rdamsc.pipeline.ingest_rdamsc_crosswalk_docs",
        fake_ingest,
    )

    result = run_bootstrap_pipeline(store, tmp_path)
    processed = cast(list[dict[str, object]], result["processed"])
    assert len(processed) == 2
    by_id = {
        cast(str, x["crosswalk_id"]): cast(dict[str, object], x["result"])
        for x in processed
    }
    assert by_id["rdamsc_c1"]["ok"] is False
    assert by_id["rdamsc_c1"]["reason"] == "exception"
    assert by_id["rdamsc_c2"]["ok"] is True


def test_pipeline_survives_catalog_sync_failure(monkeypatch, tmp_path: Path) -> None:
    store = InMemoryCrosswalkStore()
    _ = store.upsert_crosswalk(
        CrosswalkRecord(
            id="rdamsc_c1",
            name="One",
            source_standard_id="s1",
            target_standard_id="t1",
            msc_id="msc:c1",
        )
    )

    def _raise_sync(*_args, **_kwargs):
        raise RuntimeError("sync down")

    monkeypatch.setattr("kaigraph.rdamsc.pipeline.sync_rdamsc_catalog", _raise_sync)
    monkeypatch.setattr(
        "kaigraph.rdamsc.pipeline.pipeline_status_path",
        lambda: tmp_path / "rdamsc_pipeline_status.json",
    )
    monkeypatch.setattr(
        "kaigraph.rdamsc.pipeline.ingest_rdamsc_crosswalk_docs",
        lambda *_args, **_kwargs: {
            "ok": True,
            "crosswalk_id": "rdamsc_c1",
            "inserted_rules": 1,
            "total_rules": 1,
        },
    )

    logs: list[str] = []
    result = run_bootstrap_pipeline(store, tmp_path, logger=logs.append)
    assert result["synced"] == 0
    assert any("Catalog sync failed" in line for line in logs)
    processed = cast(list[dict[str, object]], result["processed"])
    assert len(processed) == 1
    assert cast(dict[str, object], processed[0]["result"])["ok"] is True


def test_pipeline_persists_status_from_typed_result_transitions(
    monkeypatch, tmp_path: Path
) -> None:
    store = InMemoryCrosswalkStore()
    _ = store.upsert_crosswalk(
        CrosswalkRecord(
            id="rdamsc_ok",
            name="OK",
            source_standard_id="s1",
            target_standard_id="t1",
            msc_id="msc:ok",
        )
    )
    _ = store.upsert_crosswalk(
        CrosswalkRecord(
            id="rdamsc_fail",
            name="Fail",
            source_standard_id="s1",
            target_standard_id="t1",
            msc_id="msc:fail",
        )
    )

    monkeypatch.setattr("kaigraph.rdamsc.pipeline.sync_rdamsc_catalog", lambda *_: 0)
    monkeypatch.setattr(
        "kaigraph.rdamsc.pipeline.pipeline_status_path",
        lambda: tmp_path / "rdamsc_pipeline_status.json",
    )

    def _fake_ingest(*args, **_kwargs):
        crosswalk_id = cast(str, args[1])
        if crosswalk_id == "rdamsc_ok":
            return {
                "ok": True,
                "crosswalk_id": crosswalk_id,
                "inserted_rules": 2,
                "total_rules": 2,
            }
        return {
            "ok": False,
            "crosswalk_id": crosswalk_id,
            "reason": "artifacts_unsupported",
            "artifact_checks": [],
            "skipped": [],
        }

    monkeypatch.setattr(
        "kaigraph.rdamsc.pipeline.ingest_rdamsc_crosswalk_docs", _fake_ingest
    )

    result = run_bootstrap_pipeline(store, tmp_path)
    processed = cast(list[dict[str, object]], result["processed"])
    assert len(processed) == 2

    status_map = load_pipeline_status()
    assert status_map["rdamsc_ok"]["status"] == "ready"
    assert status_map["rdamsc_fail"]["status"] == "failed_unsupported"


def test_resolve_status_does_not_keep_stale_ready_without_sssom(tmp_path: Path) -> None:
    store = InMemoryCrosswalkStore()
    crosswalk = CrosswalkRecord(
        id="rdamsc_c1",
        name="One",
        source_standard_id="s1",
        target_standard_id="t1",
        msc_id="msc:c1",
    )

    status = resolve_crosswalk_status(
        store,
        crosswalk,
        tmp_path,
        {
            "rdamsc_c1": {
                "status": "ready",
                "result": {"ok": True, "step": "skipped_ready"},
            }
        },
    )
    assert status == "missing_sssom"


def test_resolve_status_keeps_failure_state_without_sssom(tmp_path: Path) -> None:
    store = InMemoryCrosswalkStore()
    crosswalk = CrosswalkRecord(
        id="rdamsc_c1",
        name="One",
        source_standard_id="s1",
        target_standard_id="t1",
        msc_id="msc:c1",
    )

    status = resolve_crosswalk_status(
        store,
        crosswalk,
        tmp_path,
        {
            "rdamsc_c1": {
                "status": "failed_parse",
                "result": {"ok": False, "reason": "no_rules_extracted"},
            }
        },
    )
    assert status == "failed_parse"


def test_resolve_status_keeps_missing_state_without_sssom(tmp_path: Path) -> None:
    store = InMemoryCrosswalkStore()
    crosswalk = CrosswalkRecord(
        id="rdamsc_c1",
        name="One",
        source_standard_id="s1",
        target_standard_id="t1",
        msc_id="msc:c1",
    )

    status = resolve_crosswalk_status(
        store,
        crosswalk,
        tmp_path,
        {
            "rdamsc_c1": {
                "status": "missing_sssom",
                "result": {"ok": False, "reason": "no_rules_extracted"},
            }
        },
    )
    assert status == "missing_sssom"


def test_status_from_result_defaults_unknown_reasons_to_failed_parse() -> None:
    status = status_from_result(
        {
            "ok": False,
            "reason": "unknown_failure_mode",
            "crosswalk_id": "rdamsc_c1",
        }
    )
    assert status == "failed_parse"
