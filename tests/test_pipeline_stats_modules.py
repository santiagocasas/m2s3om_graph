import json
from pathlib import Path

import pytest

from m2s3om_graph.rdamsc.pipeline_stats_freeze import (
    write_pipeline_log_snapshot,
    write_sssom_provenance,
)
from m2s3om_graph.rdamsc.pipeline_stats_shared import (
    compute_stats,
    load_status_map,
    write_csv,
)


def test_load_status_map_requires_json_object(tmp_path: Path) -> None:
    path = tmp_path / "status.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError):
        _ = load_status_map(path)


def test_compute_stats_reports_expected_summary_and_failed_parse_subset() -> None:
    status_map = {
        "cw1": {
            "msc_id": "msc:1",
            "name": "One",
            "status": "ready",
            "label": "ready",
            "result": {
                "ok": True,
                "strategy": "deterministic_pdf",
                "artifact_checks": [
                    {
                        "status": "fetched",
                        "extension": "pdf",
                        "location_type": "Document",
                        "resolved_url": "https://example.org/a.pdf",
                        "content_type": "application/pdf",
                        "text_chars": 123,
                    }
                ],
            },
        },
        "cw2": {
            "msc_id": "msc:2",
            "name": "Two",
            "status": "failed_parse",
            "label": "failed",
            "result": {
                "ok": False,
                "reason": "no_rules_extracted",
                "artifact_checks": [
                    {
                        "status": "fetched",
                        "extension": "html",
                        "location_type": "Document",
                        "resolved_url": "https://example.org/b.html",
                        "content_type": "text/html",
                        "text_chars": 99,
                    }
                ],
            },
        },
    }

    stats = compute_stats(status_map, top_n=5)
    assert stats.summary["total_crosswalks"] == 2
    assert stats.summary["status_counts"] == {"ready": 1, "failed_parse": 1}

    artifact_summary = stats.summary["artifact_checks"]
    assert isinstance(artifact_summary, dict)
    assert artifact_summary["total"] == 2
    assert artifact_summary["fetch_success_rate_pct"] == 100.0
    assert stats.summary["failed_parse_all_artifacts_fetched"] == ["msc:2"]


def test_write_csv_writes_blank_for_empty_rows(tmp_path: Path) -> None:
    out = tmp_path / "rows.csv"
    write_csv(out, [])
    assert out.read_text(encoding="utf-8") == ""


def test_write_pipeline_log_snapshot_copy_and_placeholder(tmp_path: Path) -> None:
    source = tmp_path / "pipeline.log"
    target = tmp_path / "snap" / "pipeline.log"

    source.write_text("hello", encoding="utf-8")
    assert write_pipeline_log_snapshot(source, target) == "copied"
    assert target.read_text(encoding="utf-8") == "hello"

    missing_source = tmp_path / "missing.log"
    placeholder_target = tmp_path / "snap2" / "pipeline.log"
    assert (
        write_pipeline_log_snapshot(missing_source, placeholder_target) == "placeholder"
    )
    assert "No persisted pipeline runtime log" in placeholder_target.read_text(
        encoding="utf-8"
    )


def test_write_sssom_provenance_writes_manifest_and_markdown(tmp_path: Path) -> None:
    sssom_dir = tmp_path / "sssom"
    freeze_dir = tmp_path / "freeze"
    status_file = tmp_path / "status.json"
    status_file.write_text("{}", encoding="utf-8")

    sssom_file = sssom_dir / "rdamsc_x.sssom.tsv"
    sssom_dir.mkdir(parents=True, exist_ok=True)
    sssom_file.write_text("subject_id\tobject_id\n", encoding="utf-8")

    write_sssom_provenance(
        sssom_dir=sssom_dir,
        freeze_dir=freeze_dir,
        status_file=status_file,
        summary={
            "total_crosswalks": 1,
            "status_counts": {"ready": 1},
            "reason_counts": {},
        },
        git_meta={"commit_short": "abc", "branch": "main", "is_dirty": False},
        env_meta={"M2S3OM_DB_URL": ""},
        command_line="python scripts/rdamsc_pipeline_stats.py freeze",
    )

    manifest_path = sssom_dir / "generation_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["sssom_file_count"] == 1
    assert manifest["sssom_files"][0]["file"] == "rdamsc_x.sssom.tsv"

    md_path = sssom_dir / "GENERATED_FROM_PIPELINE.md"
    assert md_path.exists()
    assert "Generated SSSOM provenance" in md_path.read_text(encoding="utf-8")
