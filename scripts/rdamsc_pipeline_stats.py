#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import shlex
import shutil
import statistics
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

StatusMap = dict[str, dict[str, object]]


@dataclass
class StatsResult:
    summary: dict[str, object]
    crosswalk_rows: list[dict[str, object]]
    artifact_rows: list[dict[str, object]]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _default_status_file() -> Path:
    return _repo_root() / ".local" / "rdamsc_pipeline_status.json"


def _default_pipeline_log_file() -> Path:
    return _repo_root() / ".local" / "bootstrap_rdamsc.log"


def _default_freeze_dir() -> Path:
    return _repo_root() / "exports" / "pipeline" / "latest"


def _default_sssom_dir() -> Path:
    return _repo_root() / "exports" / "sssom"


def _load_status_map(path: Path) -> StatusMap:
    if not path.exists():
        raise FileNotFoundError(f"Status file not found: {path}")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError("Status file must contain a JSON object")
    out: StatusMap = {}
    for key, value in loaded.items():
        if isinstance(key, str) and isinstance(value, dict):
            out[key] = value
    return out


def _percentile(sorted_values: list[int], percentile: float) -> int:
    if not sorted_values:
        return 0
    if len(sorted_values) == 1:
        return sorted_values[0]
    idx = round((percentile / 100.0) * (len(sorted_values) - 1))
    return sorted_values[idx]


def _counter_to_dict(
    counter: Counter[str], *, top_n: int | None = None
) -> dict[str, int]:
    items = counter.most_common(top_n)
    return {k: v for k, v in items}


def _to_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


def compute_stats(status_map: StatusMap, *, top_n: int = 10) -> StatsResult:
    status_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    strategy_counts: Counter[str] = Counter()

    artifact_status_counts: Counter[str] = Counter()
    extension_fetched: Counter[str] = Counter()
    extension_errors: Counter[str] = Counter()
    location_type_counts: Counter[str] = Counter()
    content_type_counts: Counter[str] = Counter()
    host_fetched_counts: Counter[str] = Counter()
    host_error_counts: Counter[str] = Counter()

    text_sizes: list[int] = []
    failed_parse_all_fetched: list[str] = []

    crosswalk_rows: list[dict[str, object]] = []
    artifact_rows: list[dict[str, object]] = []

    for crosswalk_id, entry in status_map.items():
        msc_id = str(entry.get("msc_id", ""))
        name = str(entry.get("name", ""))
        status = str(entry.get("status", "unknown"))
        label = str(entry.get("label", status))
        status_counts[status] += 1

        result = entry.get("result")
        result_obj: dict[str, Any] = result if isinstance(result, dict) else {}
        reason = str(result_obj.get("reason", ""))
        if reason:
            reason_counts[reason] += 1

        strategy = str(result_obj.get("strategy", ""))
        if strategy:
            strategy_counts[strategy] += 1

        checks = result_obj.get("artifact_checks")
        artifact_checks = checks if isinstance(checks, list) else []

        fetched_for_crosswalk = 0
        failed_for_crosswalk = 0
        all_fetched = bool(artifact_checks)

        for idx, check in enumerate(artifact_checks, start=1):
            if not isinstance(check, dict):
                continue
            check_status = str(check.get("status", ""))
            extension = str(check.get("extension", "(unknown)"))
            location_type = str(check.get("location_type", ""))
            resolved_url = str(check.get("resolved_url") or check.get("url") or "")
            host = urlparse(resolved_url).netloc
            content_type = str(check.get("content_type", ""))
            text_chars = check.get("text_chars")

            artifact_status_counts[check_status] += 1
            if location_type:
                location_type_counts[location_type] += 1

            if check_status == "fetched":
                fetched_for_crosswalk += 1
                extension_fetched[extension] += 1
                if host:
                    host_fetched_counts[host] += 1
                if content_type:
                    content_type_counts[content_type] += 1
                if isinstance(text_chars, int):
                    text_sizes.append(text_chars)
            else:
                failed_for_crosswalk += 1
                extension_errors[extension] += 1
                if host:
                    host_error_counts[host] += 1
                all_fetched = False

            artifact_rows.append(
                {
                    "crosswalk_id": crosswalk_id,
                    "msc_id": msc_id,
                    "status": status,
                    "reason": reason,
                    "artifact_index": idx,
                    "url": str(check.get("url", "")),
                    "resolved_url": resolved_url,
                    "host": host,
                    "extension": extension,
                    "location_type": location_type,
                    "check_status": check_status,
                    "content_type": content_type,
                    "text_chars": text_chars if isinstance(text_chars, int) else "",
                }
            )

        if status == "failed_parse" and all_fetched:
            failed_parse_all_fetched.append(msc_id or crosswalk_id)

        crosswalk_rows.append(
            {
                "crosswalk_id": crosswalk_id,
                "msc_id": msc_id,
                "name": name,
                "status": status,
                "label": label,
                "reason": reason,
                "strategy": strategy,
                "result_ok": bool(result_obj.get("ok")),
                "inserted_rules": result_obj.get("inserted_rules", ""),
                "total_rules": result_obj.get("total_rules", ""),
                "backfilled_rules": result_obj.get("backfilled_rules", ""),
                "artifact_documents": result_obj.get("artifact_documents", ""),
                "artifact_chunks": result_obj.get("artifact_chunks", ""),
                "artifact_total": len(artifact_checks),
                "artifact_fetched": fetched_for_crosswalk,
                "artifact_failed": failed_for_crosswalk,
                "updated_at": str(entry.get("updated_at", "")),
            }
        )

    total_crosswalks = len(status_map)
    total_checks = sum(artifact_status_counts.values())
    fetched_checks = artifact_status_counts.get("fetched", 0)
    fetch_success_rate = (
        round((fetched_checks / total_checks) * 100, 2) if total_checks else 0.0
    )

    sorted_sizes = sorted(text_sizes)
    text_size_stats: dict[str, int | float] = {}
    if sorted_sizes:
        text_size_stats = {
            "min": sorted_sizes[0],
            "median": int(statistics.median(sorted_sizes)),
            "mean": round(statistics.mean(sorted_sizes), 2),
            "p90": _percentile(sorted_sizes, 90),
            "max": sorted_sizes[-1],
        }

    summary: dict[str, object] = {
        "generated_at": _now_iso(),
        "total_crosswalks": total_crosswalks,
        "status_counts": _counter_to_dict(status_counts),
        "status_rates": {
            k: round((v / total_crosswalks) * 100, 2) if total_crosswalks else 0.0
            for k, v in _counter_to_dict(status_counts).items()
        },
        "reason_counts": _counter_to_dict(reason_counts),
        "strategy_counts": _counter_to_dict(strategy_counts),
        "artifact_checks": {
            "total": total_checks,
            "status_counts": _counter_to_dict(artifact_status_counts),
            "fetch_success_rate_pct": fetch_success_rate,
            "extension_fetched": _counter_to_dict(extension_fetched),
            "extension_errors": _counter_to_dict(extension_errors),
            "location_types": _counter_to_dict(location_type_counts),
            "content_types_top": _counter_to_dict(content_type_counts, top_n=top_n),
            "text_size_chars": text_size_stats,
            "hosts_fetched_top": _counter_to_dict(host_fetched_counts, top_n=top_n),
            "hosts_error_top": _counter_to_dict(host_error_counts, top_n=top_n),
        },
        "failed_parse_all_artifacts_fetched": sorted(failed_parse_all_fetched),
    }
    return StatsResult(
        summary=summary,
        crosswalk_rows=sorted(crosswalk_rows, key=lambda x: str(x["msc_id"])),
        artifact_rows=sorted(
            artifact_rows,
            key=lambda x: (
                str(x.get("msc_id", "")),
                _to_int(x.get("artifact_index", 0), default=0),
            ),
        ),
    )


def _print_counter(title: str, data: dict[str, int]) -> None:
    print(f"\n{title}")
    if not data:
        print("  (none)")
        return
    for key, value in data.items():
        print(f"  - {key}: {value}")


def print_summary(summary: dict[str, object], *, top_n: int) -> None:
    total = _to_int(summary.get("total_crosswalks", 0), default=0)
    print(f"\nRDAMSC pipeline statistics ({summary.get('generated_at', '')})")
    print(f"Total crosswalks: {total}")

    status_counts = summary.get("status_counts")
    status_rates = summary.get("status_rates")
    if isinstance(status_counts, dict):
        print("\nStatus counts")
        for key, value in status_counts.items():
            rate = ""
            if isinstance(status_rates, dict) and key in status_rates:
                rate = f" ({status_rates[key]}%)"
            print(f"  - {key}: {value}{rate}")

    reason_counts = summary.get("reason_counts")
    if isinstance(reason_counts, dict):
        _print_counter("Failure reasons", reason_counts)

    strategy_counts = summary.get("strategy_counts")
    if isinstance(strategy_counts, dict):
        _print_counter("Extraction strategy", strategy_counts)

    artifact_info = summary.get("artifact_checks")
    if not isinstance(artifact_info, dict):
        return

    print("\nArtifact checks")
    print(f"  - total checks: {artifact_info.get('total', 0)}")
    print(f"  - fetch success rate: {artifact_info.get('fetch_success_rate_pct', 0)}%")

    status_counts_art = artifact_info.get("status_counts")
    if isinstance(status_counts_art, dict):
        _print_counter("Artifact check status", status_counts_art)

    ext_ok = artifact_info.get("extension_fetched")
    if isinstance(ext_ok, dict):
        _print_counter(
            f"Fetched extensions (top {top_n})", dict(list(ext_ok.items())[:top_n])
        )

    ext_err = artifact_info.get("extension_errors")
    if isinstance(ext_err, dict):
        _print_counter(
            f"Errored extensions (top {top_n})", dict(list(ext_err.items())[:top_n])
        )

    hosts_err = artifact_info.get("hosts_error_top")
    if isinstance(hosts_err, dict):
        _print_counter(
            f"Hosts with fetch errors (top {top_n})",
            dict(list(hosts_err.items())[:top_n]),
        )

    text_stats = artifact_info.get("text_size_chars")
    if isinstance(text_stats, dict) and text_stats:
        print(
            "\nFetched text size chars "
            f"(min/median/p90/max): {text_stats.get('min')}/"
            f"{text_stats.get('median')}/{text_stats.get('p90')}/{text_stats.get('max')}"
        )

    parse_fetched = summary.get("failed_parse_all_artifacts_fetched")
    if isinstance(parse_fetched, list):
        print("\nfailed_parse with all artifacts fetched")
        if not parse_fetched:
            print("  (none)")
        else:
            for item in parse_fetched:
                print(f"  - {item}")


def _write_json(path: Path, obj: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _git_output(repo_root: Path, args: list[str]) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return ""
    return completed.stdout.strip()


def _git_metadata(repo_root: Path) -> dict[str, object]:
    status_short = _git_output(repo_root, ["status", "--short"])
    return {
        "repo_root": str(repo_root),
        "commit": _git_output(repo_root, ["rev-parse", "HEAD"]),
        "commit_short": _git_output(repo_root, ["rev-parse", "--short", "HEAD"]),
        "commit_date": _git_output(repo_root, ["show", "-s", "--format=%cI", "HEAD"]),
        "branch": _git_output(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]),
        "remote_origin": _git_output(repo_root, ["remote", "get-url", "origin"]),
        "is_dirty": bool(status_short),
    }


def _env_metadata() -> dict[str, object]:
    keys = [
        "KAIGRAPH_USE_SURREAL",
        "KAIGRAPH_DB_URL",
        "KAIGRAPH_DB_NS",
        "KAIGRAPH_DB_NAME",
        "BLABLADOR_BASE_URL",
        "KAIGRAPH_LLM_MODEL",
    ]
    out: dict[str, object] = {key: os.getenv(key, "") for key in keys}
    out["BLABLADOR_API_KEY_loaded"] = bool(os.getenv("BLABLADOR_API_KEY"))
    return out


def _relative_path(path: Path, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except Exception:
        return str(path.resolve())


def _write_pipeline_log_snapshot(source_log: Path, target_log: Path) -> str:
    target_log.parent.mkdir(parents=True, exist_ok=True)
    if source_log.exists():
        shutil.copy2(source_log, target_log)
        return "copied"
    note = (
        "No persisted pipeline runtime log was found at freeze time.\n"
        "This snapshot was generated from the pipeline status JSON.\n"
        f"Expected log path: {source_log}\n"
    )
    target_log.write_text(note, encoding="utf-8")
    return "placeholder"


def _write_sssom_provenance(
    *,
    sssom_dir: Path,
    freeze_dir: Path,
    status_file: Path,
    summary: dict[str, object],
    git_meta: dict[str, object],
    env_meta: dict[str, object],
    command_line: str,
) -> None:
    sssom_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(sssom_dir.glob("*.sssom.tsv"))

    file_rows: list[dict[str, object]] = []
    for path in files:
        stat = path.stat()
        file_rows.append(
            {
                "file": path.name,
                "sha256": _sha256_file(path),
                "size_bytes": stat.st_size,
                "mtime_utc": datetime.fromtimestamp(
                    stat.st_mtime,
                    tz=timezone.utc,
                ).isoformat(),
            }
        )

    manifest = {
        "generated_at": _now_iso(),
        "purpose": "Provenance for committed SSSOM files generated by RDAMSC pipeline",
        "command": command_line,
        "status_file": str(status_file.resolve()),
        "freeze_snapshot_dir": str(freeze_dir.resolve()),
        "git": git_meta,
        "environment": env_meta,
        "pipeline_summary": {
            "total_crosswalks": summary.get("total_crosswalks", 0),
            "status_counts": summary.get("status_counts", {}),
            "reason_counts": summary.get("reason_counts", {}),
        },
        "sssom_file_count": len(file_rows),
        "sssom_files": file_rows,
        "note": (
            "Pipeline logic, prompts, model backends, and retrieval strategy can change. "
            "Use git commit metadata and file checksums for reproducibility."
        ),
    }
    _write_json(sssom_dir / "generation_manifest.json", manifest)

    md_lines = [
        "# Generated SSSOM provenance",
        "",
        "These SSSOM files were generated from the RDAMSC pipeline and frozen for commit.",
        "",
        f"- Generated at (UTC): `{manifest['generated_at']}`",
        f"- Commit: `{git_meta.get('commit_short')}` ({git_meta.get('branch')})",
        f"- Dirty working tree at freeze time: `{git_meta.get('is_dirty')}`",
        f"- Pipeline status source: `{status_file.resolve()}`",
        f"- Frozen analytics snapshot: `{freeze_dir.resolve()}`",
        f"- SSSOM files included: `{len(file_rows)}`",
        "",
        "## Summary",
        f"- Total crosswalks: `{summary.get('total_crosswalks', 0)}`",
        f"- Status counts: `{summary.get('status_counts', {})}`",
        f"- Failure reasons: `{summary.get('reason_counts', {})}`",
        "",
        "## Reproducibility",
        "- See `generation_manifest.json` in this directory for checksums and metadata.",
        "- See `exports/pipeline/latest/` for status, stats CSV/JSON, and plots.",
        "",
        "## Caveat",
        "- LLM outputs and external artifact availability may vary over time.",
    ]
    (sssom_dir / "GENERATED_FROM_PIPELINE.md").write_text(
        "\n".join(md_lines) + "\n",
        encoding="utf-8",
    )


def _save_plots(summary: dict[str, object], out_dir: Path, *, top_n: int) -> None:
    try:
        import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
    except Exception as exc:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "matplotlib is required for --plots-dir. "
            "Try: uv run --with matplotlib python scripts/rdamsc_pipeline_stats.py stats ..."
        ) from exc

    out_dir.mkdir(parents=True, exist_ok=True)

    def _bar_plot(
        values: dict[str, int],
        *,
        title: str,
        x_label: str,
        y_label: str,
        file_name: str,
    ) -> None:
        if not values:
            return
        labels = list(values.keys())
        counts = list(values.values())

        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(labels, counts)
        ax.set_title(title)
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.tick_params(axis="x", labelrotation=45)
        fig.tight_layout()
        fig.savefig(out_dir / file_name, dpi=150)
        plt.close(fig)

    status_counts = summary.get("status_counts")
    if isinstance(status_counts, dict):
        _bar_plot(
            {str(k): int(v) for k, v in status_counts.items()},
            title="Crosswalk status counts",
            x_label="status",
            y_label="count",
            file_name="status_counts.png",
        )

    reason_counts = summary.get("reason_counts")
    if isinstance(reason_counts, dict):
        _bar_plot(
            {str(k): int(v) for k, v in reason_counts.items()},
            title="Failure reasons",
            x_label="reason",
            y_label="count",
            file_name="failure_reasons.png",
        )

    artifact_checks = summary.get("artifact_checks")
    if isinstance(artifact_checks, dict):
        ext_ok = artifact_checks.get("extension_fetched")
        if isinstance(ext_ok, dict):
            _bar_plot(
                {str(k): int(v) for k, v in list(ext_ok.items())[:top_n]},
                title=f"Fetched artifact extensions (top {top_n})",
                x_label="extension",
                y_label="count",
                file_name="extensions_fetched.png",
            )

        ext_err = artifact_checks.get("extension_errors")
        if isinstance(ext_err, dict):
            _bar_plot(
                {str(k): int(v) for k, v in list(ext_err.items())[:top_n]},
                title=f"Errored artifact extensions (top {top_n})",
                x_label="extension",
                y_label="count",
                file_name="extensions_errors.png",
            )

        hosts_err = artifact_checks.get("hosts_error_top")
        if isinstance(hosts_err, dict):
            _bar_plot(
                {str(k): int(v) for k, v in list(hosts_err.items())[:top_n]},
                title=f"Hosts with fetch errors (top {top_n})",
                x_label="host",
                y_label="count",
                file_name="hosts_errors.png",
            )


def run_command(args: argparse.Namespace) -> int:
    from kaigraph.db import build_default_store
    from kaigraph.rdamsc.pipeline import run_bootstrap_pipeline

    store = build_default_store()
    out_dir = Path(args.sssom_dir)

    logger = None
    if not args.quiet:

        def _logger(message: str) -> None:
            print(message, flush=True)

        logger = _logger

    result = run_bootstrap_pipeline(
        store,
        out_dir,
        force=bool(args.force),
        only_crosswalk_id=(args.crosswalk_id or None),
        logger=logger,
    )
    processed = result.get("processed")
    processed_count = len(processed) if isinstance(processed, list) else 0
    print(
        json.dumps(
            {
                "synced": result.get("synced", 0),
                "processed": processed_count,
                "status_file": result.get("status_file", ""),
            },
            ensure_ascii=True,
        )
    )

    if args.with_stats:
        status_file = Path(str(result.get("status_file", _default_status_file())))
        return stats_command(
            argparse.Namespace(
                status_file=status_file,
                top_n=args.top_n,
                json_out=args.json_out,
                crosswalk_csv_out=args.crosswalk_csv_out,
                artifact_csv_out=args.artifact_csv_out,
                plots_dir=args.plots_dir,
                print_json=False,
            )
        )
    return 0


def freeze_command(args: argparse.Namespace) -> int:
    repo_root = _repo_root()
    status_file = Path(args.status_file)
    output_dir = Path(args.output_dir)
    sssom_dir = Path(args.sssom_dir)
    pipeline_log = Path(args.pipeline_log)
    top_n = int(args.top_n)

    status_map = _load_status_map(status_file)
    stats = compute_stats(status_map, top_n=top_n)
    print_summary(stats.summary, top_n=top_n)

    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(status_file, output_dir / "rdamsc_pipeline_status.json")
    _write_json(output_dir / "rdamsc_stats_summary.json", stats.summary)
    _write_csv(output_dir / "rdamsc_crosswalks.csv", stats.crosswalk_rows)
    _write_csv(output_dir / "rdamsc_artifacts.csv", stats.artifact_rows)

    plots_dir = output_dir / "plots"
    if bool(args.plots):
        if plots_dir.exists():
            shutil.rmtree(plots_dir)
        _save_plots(stats.summary, plots_dir, top_n=top_n)

    log_mode = _write_pipeline_log_snapshot(pipeline_log, output_dir / "pipeline.log")

    git_meta = _git_metadata(repo_root)
    env_meta = _env_metadata()
    command_line = " ".join(shlex.quote(part) for part in sys.argv)

    run_metadata = {
        "generated_at": _now_iso(),
        "command": command_line,
        "status_file_used": str(status_file.resolve()),
        "status_file_copied_to": str(
            (output_dir / "rdamsc_pipeline_status.json").resolve()
        ),
        "pipeline_log_source": str(pipeline_log.resolve()),
        "pipeline_log_mode": log_mode,
        "git": git_meta,
        "environment": env_meta,
        "summary": {
            "total_crosswalks": stats.summary.get("total_crosswalks", 0),
            "status_counts": stats.summary.get("status_counts", {}),
            "reason_counts": stats.summary.get("reason_counts", {}),
        },
    }
    _write_json(output_dir / "run_metadata.json", run_metadata)

    _write_sssom_provenance(
        sssom_dir=sssom_dir,
        freeze_dir=output_dir,
        status_file=status_file,
        summary=stats.summary,
        git_meta=git_meta,
        env_meta=env_meta,
        command_line=command_line,
    )

    if args.print_json:
        print("\nJSON summary")
        print(json.dumps(stats.summary, indent=2, ensure_ascii=True))

    print("\nFreeze outputs")
    print(f"  - Snapshot dir: {output_dir}")
    print(f"  - SSSOM provenance: {sssom_dir / 'generation_manifest.json'}")
    print(f"  - SSSOM summary: {sssom_dir / 'GENERATED_FROM_PIPELINE.md'}")
    return 0


def stats_command(args: argparse.Namespace) -> int:
    status_file = Path(args.status_file)
    status_map = _load_status_map(status_file)
    stats = compute_stats(status_map, top_n=int(args.top_n))
    print_summary(stats.summary, top_n=int(args.top_n))

    if args.print_json:
        print("\nJSON summary")
        print(json.dumps(stats.summary, indent=2, ensure_ascii=True))

    if args.json_out:
        out_path = Path(args.json_out)
        _write_json(out_path, stats.summary)
        print(f"\nWrote JSON summary: {out_path}")
    if args.crosswalk_csv_out:
        out_path = Path(args.crosswalk_csv_out)
        _write_csv(out_path, stats.crosswalk_rows)
        print(f"Wrote crosswalk CSV: {out_path}")
    if args.artifact_csv_out:
        out_path = Path(args.artifact_csv_out)
        _write_csv(out_path, stats.artifact_rows)
        print(f"Wrote artifact CSV: {out_path}")
    if args.plots_dir:
        out_dir = Path(args.plots_dir)
        _save_plots(stats.summary, out_dir, top_n=int(args.top_n))
        print(f"Wrote plots: {out_dir}")

    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run RDAMSC bootstrap pipeline and generate statistics"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run full RDAMSC pipeline")
    run.add_argument(
        "--sssom-dir",
        default="exports/sssom",
        help="Directory where .sssom.tsv files are written",
    )
    run.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even if a crosswalk is already ready",
    )
    run.add_argument(
        "--crosswalk-id",
        default="",
        help="Run for one crosswalk id only",
    )
    run.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress step-by-step pipeline logs",
    )
    run.add_argument(
        "--with-stats",
        action="store_true",
        help="After run, compute and print statistics from status file",
    )
    run.add_argument("--top-n", type=int, default=10, help="Top-N entries in reports")
    run.add_argument(
        "--json-out",
        default="",
        help="Optional path for JSON summary (used with --with-stats)",
    )
    run.add_argument(
        "--crosswalk-csv-out",
        default="",
        help="Optional path for crosswalk-level CSV (used with --with-stats)",
    )
    run.add_argument(
        "--artifact-csv-out",
        default="",
        help="Optional path for artifact-level CSV (used with --with-stats)",
    )
    run.add_argument(
        "--plots-dir",
        default="",
        help="Optional directory for PNG plots (used with --with-stats)",
    )

    stats = sub.add_parser("stats", help="Generate statistics from a status JSON file")
    stats.add_argument(
        "--status-file",
        default=str(_default_status_file()),
        help="Path to rdamsc_pipeline_status.json",
    )
    stats.add_argument("--top-n", type=int, default=10, help="Top-N entries in reports")
    stats.add_argument(
        "--json-out",
        default="",
        help="Optional path for summary JSON output",
    )
    stats.add_argument(
        "--crosswalk-csv-out",
        default="",
        help="Optional path for crosswalk-level CSV output",
    )
    stats.add_argument(
        "--artifact-csv-out",
        default="",
        help="Optional path for artifact-level CSV output",
    )
    stats.add_argument(
        "--plots-dir",
        default="",
        help="Optional directory for PNG plots",
    )
    stats.add_argument(
        "--print-json",
        action="store_true",
        help="Print full JSON summary to stdout",
    )

    freeze = sub.add_parser(
        "freeze",
        help=(
            "Freeze existing pipeline outputs into tracked exports folder "
            "without re-running the pipeline"
        ),
    )
    freeze.add_argument(
        "--status-file",
        default=str(_default_status_file()),
        help="Path to existing rdamsc_pipeline_status.json",
    )
    freeze.add_argument(
        "--output-dir",
        default=str(_default_freeze_dir()),
        help="Tracked output folder for status/stats/log/plots",
    )
    freeze.add_argument(
        "--sssom-dir",
        default=str(_default_sssom_dir()),
        help="SSSOM folder where provenance files are written",
    )
    freeze.add_argument(
        "--pipeline-log",
        default=str(_default_pipeline_log_file()),
        help="Optional source log file to snapshot into output-dir/pipeline.log",
    )
    freeze.add_argument(
        "--top-n", type=int, default=10, help="Top-N entries in reports"
    )
    freeze.add_argument(
        "--plots",
        action="store_true",
        help="Generate PNG plots into <output-dir>/plots (requires matplotlib)",
    )
    freeze.add_argument(
        "--print-json",
        action="store_true",
        help="Print full JSON summary to stdout",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "run":
        return run_command(args)
    if args.command == "stats":
        return stats_command(args)
    if args.command == "freeze":
        return freeze_command(args)
    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
