from __future__ import annotations

import argparse
import json
import shlex
import sys
from pathlib import Path

from .pipeline_stats_freeze import (
    default_freeze_dir,
    default_pipeline_log_file,
    default_sssom_dir,
    default_status_file,
    freeze_outputs,
)
from .pipeline_stats_shared import (
    compute_stats,
    load_status_map,
    print_summary,
    save_plots,
    write_csv,
    write_json,
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
        status_file = Path(str(result.get("status_file", default_status_file())))
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


def stats_command(args: argparse.Namespace) -> int:
    status_file = Path(args.status_file)
    status_map = load_status_map(status_file)
    stats = compute_stats(status_map, top_n=int(args.top_n))
    print_summary(stats.summary, top_n=int(args.top_n))

    if args.print_json:
        print("\nJSON summary")
        print(json.dumps(stats.summary, indent=2, ensure_ascii=True))

    if args.json_out:
        out_path = Path(args.json_out)
        write_json(out_path, stats.summary)
        print(f"\nWrote JSON summary: {out_path}")
    if args.crosswalk_csv_out:
        out_path = Path(args.crosswalk_csv_out)
        write_csv(out_path, stats.crosswalk_rows)
        print(f"Wrote crosswalk CSV: {out_path}")
    if args.artifact_csv_out:
        out_path = Path(args.artifact_csv_out)
        write_csv(out_path, stats.artifact_rows)
        print(f"Wrote artifact CSV: {out_path}")
    if args.plots_dir:
        out_dir = Path(args.plots_dir)
        save_plots(stats.summary, out_dir, top_n=int(args.top_n))
        print(f"Wrote plots: {out_dir}")

    return 0


def freeze_command(args: argparse.Namespace) -> int:
    command_line = " ".join(shlex.quote(part) for part in sys.argv)
    return freeze_outputs(
        status_file=Path(args.status_file),
        output_dir=Path(args.output_dir),
        sssom_dir=Path(args.sssom_dir),
        pipeline_log=Path(args.pipeline_log),
        top_n=int(args.top_n),
        plots=bool(args.plots),
        print_json=bool(args.print_json),
        command_line=command_line,
    )


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
        default=str(default_status_file()),
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
        default=str(default_status_file()),
        help="Path to existing rdamsc_pipeline_status.json",
    )
    freeze.add_argument(
        "--output-dir",
        default=str(default_freeze_dir()),
        help="Tracked output folder for status/stats/log/plots",
    )
    freeze.add_argument(
        "--sssom-dir",
        default=str(default_sssom_dir()),
        help="SSSOM folder where provenance files are written",
    )
    freeze.add_argument(
        "--pipeline-log",
        default=str(default_pipeline_log_file()),
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
