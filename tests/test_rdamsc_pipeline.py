from pathlib import Path
from typing import cast

from kaigraph.db import CrosswalkRecord, InMemoryCrosswalkStore
from kaigraph.rdamsc.pipeline import resolve_crosswalk_status, run_bootstrap_pipeline


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
        "kaigraph.rdamsc.pipeline.resolve_crosswalk_status",
        lambda *_args, **_kwargs: "missing_sssom",
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
        "kaigraph.rdamsc.pipeline.resolve_crosswalk_status",
        lambda *_args, **_kwargs: "ready",
    )

    logs: list[str] = []
    result = run_bootstrap_pipeline(store, tmp_path, logger=logs.append)
    assert result["synced"] == 0
    assert any("Catalog sync failed" in line for line in logs)


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
