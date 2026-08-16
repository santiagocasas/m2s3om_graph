from __future__ import annotations

import csv
import json
import matplotlib.pyplot as plt  # pyright: ignore[reportMissingImports]
import os
import statistics
import tempfile
from collections import Counter
from dataclasses import dataclass, field
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


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_status_map(path: Path) -> StatusMap:
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


def _entry_fields(
    entry: dict[str, object],
) -> tuple[
    str,
    str,
    str,
    str,
    dict[str, Any],
    str,
    str,
    list[dict[str, object]],
]:
    msc_id = str(entry.get("msc_id", ""))
    name = str(entry.get("name", ""))
    status = str(entry.get("status", "unknown"))
    label = str(entry.get("label", status))

    result = entry.get("result")
    result_obj: dict[str, Any] = result if isinstance(result, dict) else {}
    reason = str(result_obj.get("reason", ""))
    strategy = str(result_obj.get("strategy", ""))

    checks = result_obj.get("artifact_checks")
    raw_checks = checks if isinstance(checks, list) else []
    artifact_checks: list[dict[str, object]] = [
        x for x in raw_checks if isinstance(x, dict)
    ]
    return msc_id, name, status, label, result_obj, reason, strategy, artifact_checks


@dataclass
class _StatsAccumulator:
    status_counts: Counter[str] = field(default_factory=Counter)
    reason_counts: Counter[str] = field(default_factory=Counter)
    strategy_counts: Counter[str] = field(default_factory=Counter)

    artifact_status_counts: Counter[str] = field(default_factory=Counter)
    extension_fetched: Counter[str] = field(default_factory=Counter)
    extension_errors: Counter[str] = field(default_factory=Counter)
    location_type_counts: Counter[str] = field(default_factory=Counter)
    content_type_counts: Counter[str] = field(default_factory=Counter)
    host_fetched_counts: Counter[str] = field(default_factory=Counter)
    host_error_counts: Counter[str] = field(default_factory=Counter)

    text_sizes: list[int] = field(default_factory=list)
    failed_parse_all_fetched: list[str] = field(default_factory=list)
    crosswalk_rows: list[dict[str, object]] = field(default_factory=list)
    artifact_rows: list[dict[str, object]] = field(default_factory=list)

    def _process_artifact_checks(
        self,
        *,
        crosswalk_id: str,
        msc_id: str,
        status: str,
        reason: str,
        artifact_checks: list[dict[str, object]],
    ) -> tuple[int, int, bool]:
        fetched_for_crosswalk = 0
        failed_for_crosswalk = 0
        all_fetched = bool(artifact_checks)

        for idx, check in enumerate(artifact_checks, start=1):
            check_status = str(check.get("status", ""))
            extension = str(check.get("extension", "(unknown)"))
            location_type = str(check.get("location_type", ""))
            resolved_url = str(check.get("resolved_url") or check.get("url") or "")
            host = urlparse(resolved_url).netloc
            content_type = str(check.get("content_type", ""))
            text_chars = check.get("text_chars")

            self.artifact_status_counts[check_status] += 1
            if location_type:
                self.location_type_counts[location_type] += 1

            if check_status == "fetched":
                fetched_for_crosswalk += 1
                self.extension_fetched[extension] += 1
                if host:
                    self.host_fetched_counts[host] += 1
                if content_type:
                    self.content_type_counts[content_type] += 1
                if isinstance(text_chars, int):
                    self.text_sizes.append(text_chars)
            else:
                failed_for_crosswalk += 1
                self.extension_errors[extension] += 1
                if host:
                    self.host_error_counts[host] += 1
                all_fetched = False

            self.artifact_rows.append(
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

        return fetched_for_crosswalk, failed_for_crosswalk, all_fetched

    def add_entry(self, crosswalk_id: str, entry: dict[str, object]) -> None:
        (
            msc_id,
            name,
            status,
            label,
            result_obj,
            reason,
            strategy,
            artifact_checks,
        ) = _entry_fields(entry)

        self.status_counts[status] += 1
        if reason:
            self.reason_counts[reason] += 1
        if strategy:
            self.strategy_counts[strategy] += 1

        fetched_for_crosswalk, failed_for_crosswalk, all_fetched = (
            self._process_artifact_checks(
                crosswalk_id=crosswalk_id,
                msc_id=msc_id,
                status=status,
                reason=reason,
                artifact_checks=artifact_checks,
            )
        )

        if status == "failed_parse" and all_fetched:
            self.failed_parse_all_fetched.append(msc_id or crosswalk_id)

        self.crosswalk_rows.append(
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


def _summary_from_accumulator(
    acc: _StatsAccumulator, *, top_n: int, total: int
) -> dict[str, object]:
    total_checks = sum(acc.artifact_status_counts.values())
    fetched_checks = acc.artifact_status_counts.get("fetched", 0)
    fetch_success_rate = (
        round((fetched_checks / total_checks) * 100, 2) if total_checks else 0.0
    )

    sorted_sizes = sorted(acc.text_sizes)
    text_size_stats: dict[str, int | float] = {}
    if sorted_sizes:
        text_size_stats = {
            "min": sorted_sizes[0],
            "median": int(statistics.median(sorted_sizes)),
            "mean": round(statistics.mean(sorted_sizes), 2),
            "p90": _percentile(sorted_sizes, 90),
            "max": sorted_sizes[-1],
        }

    status_counts = _counter_to_dict(acc.status_counts)
    return {
        "generated_at": now_iso(),
        "total_crosswalks": total,
        "status_counts": status_counts,
        "status_rates": {
            k: round((v / total) * 100, 2) if total else 0.0
            for k, v in status_counts.items()
        },
        "reason_counts": _counter_to_dict(acc.reason_counts),
        "strategy_counts": _counter_to_dict(acc.strategy_counts),
        "artifact_checks": {
            "total": total_checks,
            "status_counts": _counter_to_dict(acc.artifact_status_counts),
            "fetch_success_rate_pct": fetch_success_rate,
            "extension_fetched": _counter_to_dict(acc.extension_fetched),
            "extension_errors": _counter_to_dict(acc.extension_errors),
            "location_types": _counter_to_dict(acc.location_type_counts),
            "content_types_top": _counter_to_dict(acc.content_type_counts, top_n=top_n),
            "text_size_chars": text_size_stats,
            "hosts_fetched_top": _counter_to_dict(acc.host_fetched_counts, top_n=top_n),
            "hosts_error_top": _counter_to_dict(acc.host_error_counts, top_n=top_n),
        },
        "failed_parse_all_artifacts_fetched": sorted(acc.failed_parse_all_fetched),
    }


def compute_stats(status_map: StatusMap, *, top_n: int = 10) -> StatsResult:
    acc = _StatsAccumulator()
    for crosswalk_id, entry in status_map.items():
        acc.add_entry(crosswalk_id, entry)

    summary = _summary_from_accumulator(acc, top_n=top_n, total=len(status_map))
    return StatsResult(
        summary=summary,
        crosswalk_rows=sorted(acc.crosswalk_rows, key=lambda x: str(x["msc_id"])),
        artifact_rows=sorted(
            acc.artifact_rows,
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


def _print_status_section(summary: dict[str, object]) -> None:
    status_counts = summary.get("status_counts")
    status_rates = summary.get("status_rates")
    if not isinstance(status_counts, dict):
        return

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


def _print_artifact_section(summary: dict[str, object], *, top_n: int) -> None:
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
    if not isinstance(parse_fetched, list):
        return

    print("\nfailed_parse with all artifacts fetched")
    if not parse_fetched:
        print("  (none)")
        return
    for item in parse_fetched:
        print(f"  - {item}")


def print_summary(summary: dict[str, object], *, top_n: int) -> None:
    total = _to_int(summary.get("total_crosswalks", 0), default=0)
    print(f"\nRDAMSC pipeline statistics ({summary.get('generated_at', '')})")
    print(f"Total crosswalks: {total}")
    _print_status_section(summary)
    _print_artifact_section(summary, top_n=top_n)


def write_json(path: Path, obj: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(path, json.dumps(obj, indent=2, ensure_ascii=True))


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
        ) as tmp:
            tmp.write(content)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)
        if tmp_path is not None:
            tmp_path.replace(path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        _atomic_write_text(path, "")
        return
    fieldnames = list(rows[0].keys())
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            delete=False,
        ) as tmp:
            writer = csv.DictWriter(tmp, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = Path(tmp.name)
        if tmp_path is not None:
            tmp_path.replace(path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def save_plots(summary: dict[str, object], out_dir: Path, *, top_n: int) -> None:
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
