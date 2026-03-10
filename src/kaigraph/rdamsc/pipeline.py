import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from kaigraph.db import CrosswalkRecord, CrosswalkStore
from kaigraph.sssom import load_sssom_rules

from .ingest import ingest_rdamsc_crosswalk_docs, sssom_output_path, sync_rdamsc_catalog

StatusCode = str

STATUS_LABELS: dict[StatusCode, str] = {
    "ready": "SSSOM ready",
    "kg_out_of_sync": "KG out of sync",
    "missing_sssom": "missing SSSOM",
    "failed_unreachable": "failed: docs unreachable",
    "failed_unsupported": "failed: unsupported docs",
    "failed_parse": "failed: parse/extract",
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def pipeline_status_path() -> Path:
    return _repo_root() / ".local" / "rdamsc_pipeline_status.json"


def load_pipeline_status() -> dict[str, dict[str, object]]:
    path = pipeline_status_path()
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if not isinstance(loaded, dict):
        return {}
    out: dict[str, dict[str, object]] = {}
    for key, value in loaded.items():
        if isinstance(key, str) and isinstance(value, dict):
            out[key] = value
    return out


def save_pipeline_status(status_map: dict[str, dict[str, object]]) -> Path:
    path = pipeline_status_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(status_map, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return path


def _reason_to_status(reason: str) -> StatusCode:
    if reason == "artifacts_unreachable":
        return "failed_unreachable"
    if reason == "artifacts_unsupported":
        return "failed_unsupported"
    if reason == "no_rules_extracted":
        return "failed_parse"
    return "failed_parse"


def status_label(code: StatusCode) -> str:
    return STATUS_LABELS.get(code, code)


def resolve_crosswalk_status(
    store: CrosswalkStore,
    crosswalk: CrosswalkRecord,
    output_dir: Path,
    status_map: dict[str, dict[str, object]],
) -> StatusCode:
    sssom_path = sssom_output_path(output_dir, crosswalk.id)
    sssom_rules = (
        load_sssom_rules(sssom_path, crosswalk.id) if sssom_path.exists() else []
    )
    bundle = store.get_crosswalk_bundle(crosswalk.id)
    kg_rules = len(bundle.rules) if bundle is not None else 0

    if sssom_rules:
        if kg_rules > 0:
            return "ready"
        return "kg_out_of_sync"

    last = status_map.get(crosswalk.id, {})
    last_status = last.get("status")
    if isinstance(last_status, str):
        if last_status in {
            "failed_unreachable",
            "failed_unsupported",
            "failed_parse",
        }:
            return last_status
        if last_status == "missing_sssom":
            return "missing_sssom"
    return "missing_sssom"


def backfill_kg_from_sssom(
    store: CrosswalkStore,
    crosswalk: CrosswalkRecord,
    output_dir: Path,
) -> int:
    path = sssom_output_path(output_dir, crosswalk.id)
    rules = load_sssom_rules(path, crosswalk.id)
    inserted = 0
    for rule in rules:
        _ = store.upsert_mapping_rule(rule)
        inserted += 1
    return inserted


def _update_status(
    status_map: dict[str, dict[str, object]],
    crosswalk: CrosswalkRecord,
    status: StatusCode,
    result: dict[str, object],
) -> None:
    status_map[crosswalk.id] = {
        "crosswalk_id": crosswalk.id,
        "msc_id": crosswalk.msc_id,
        "name": crosswalk.name,
        "status": status,
        "label": status_label(status),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
    }


def run_bootstrap_pipeline(
    store: CrosswalkStore,
    output_dir: Path,
    *,
    force: bool = False,
    only_crosswalk_id: str | None = None,
    logger: Callable[[str], None] | None = None,
) -> dict[str, object]:
    def emit(msg: str) -> None:
        if logger is not None:
            logger(msg)

    emit("[pipeline] Syncing RDAMSC metadata catalog")
    try:
        synced = sync_rdamsc_catalog(store)
        emit(f"[pipeline] Synced {synced} mapping metadata records")
    except Exception as exc:
        synced = 0
        emit(f"[pipeline] Catalog sync failed: {exc}")

    output_dir.mkdir(parents=True, exist_ok=True)
    status_map = load_pipeline_status()
    crosswalks = [
        x
        for x in store.list_crosswalks()
        if x.msc_id is not None and x.msc_id.startswith("msc:")
    ]
    if only_crosswalk_id:
        crosswalks = [x for x in crosswalks if x.id == only_crosswalk_id]

    processed: list[dict[str, object]] = []
    for crosswalk in crosswalks:
        emit(f"[{crosswalk.msc_id}] Checking pipeline status")
        status = resolve_crosswalk_status(store, crosswalk, output_dir, status_map)

        if status == "kg_out_of_sync" and not force:
            loaded = backfill_kg_from_sssom(store, crosswalk, output_dir)
            emit(f"[{crosswalk.msc_id}] Backfilled KG from SSSOM ({loaded} rules)")
            result: dict[str, object] = {
                "ok": True,
                "backfilled_rules": loaded,
                "step": "kg_backfill",
            }
            _update_status(status_map, crosswalk, "ready", result)
            processed.append({"crosswalk_id": crosswalk.id, "result": result})
            continue

        if status == "ready" and not force:
            emit(f"[{crosswalk.msc_id}] Skip: already ready")
            result: dict[str, object] = {"ok": True, "step": "skipped_ready"}
            _update_status(status_map, crosswalk, "ready", result)
            processed.append({"crosswalk_id": crosswalk.id, "result": result})
            continue

        emit(f"[{crosswalk.msc_id}] Ingesting mapping documentation")
        try:
            result = ingest_rdamsc_crosswalk_docs(
                store,
                crosswalk.id,
                output_dir,
                logger=logger,
            )
        except Exception as exc:
            result = {
                "ok": False,
                "reason": "exception",
                "crosswalk_id": crosswalk.id,
                "error": str(exc),
            }
            emit(f"[{crosswalk.msc_id}] Failed with exception: {exc}")
        if bool(result.get("ok")):
            emit(f"[{crosswalk.msc_id}] Ready")
            _update_status(status_map, crosswalk, "ready", result)
        else:
            reason = str(result.get("reason", "unknown"))
            mapped = _reason_to_status(reason)
            emit(f"[{crosswalk.msc_id}] Failed: {mapped} ({reason})")
            _update_status(status_map, crosswalk, mapped, result)
        processed.append({"crosswalk_id": crosswalk.id, "result": result})

    path = save_pipeline_status(status_map)
    emit(f"[pipeline] Saved status file: {path}")

    return {
        "synced": synced,
        "processed": processed,
        "status_file": str(path),
    }
