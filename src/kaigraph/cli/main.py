import argparse
import json
from pathlib import Path
from typing import Callable

from kaigraph.benchmark.report import benchmark_summary_to_json
from kaigraph.benchmark.runner import run_fixture_benchmark
from kaigraph.db import build_default_store
from kaigraph.ingest.crosswalk_ingestion import ingest_datacite_to_dc_pdf
from kaigraph.rdamsc.ingest import (
    dump_result_json,
    ensure_sssom_for_bundle,
    ingest_rdamsc_crosswalk_docs,
    sync_rdamsc_catalog,
)
from kaigraph.rdamsc.contracts import BootstrapPipelineResult, IngestResult
from kaigraph.rdamsc.pipeline import run_bootstrap_pipeline
from kaigraph.transform.apply import apply_mapping_rules
from kaigraph.transform.ir import IRValue, add_ir_value
from kaigraph.transform.serializers import ir_to_dublin_core_xml


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="kaigraph CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest-pdf", help="Ingest DataCite->DC mapping PDF")
    ingest.add_argument(
        "--pdf",
        default="/home/casas/AI/Metadata-Mappings/DataCite_DublinCore_Mapping.pdf",
    )

    sync = sub.add_parser("sync-rdamsc", help="Sync RDAMSC mapping catalog")
    sync.add_argument(
        "--with-ingest",
        action="store_true",
        help="Ingest easy artifacts after syncing",
    )
    sync.add_argument(
        "--sssom-dir",
        default="exports/sssom",
        help="Directory where .sssom.tsv files are written",
    )

    ingest_api = sub.add_parser(
        "ingest-rdamsc",
        help="Ingest mapping documentation for one/all RDAMSC crosswalks",
    )
    ingest_api.add_argument("--crosswalk-id", default="", help="Internal crosswalk id")
    ingest_api.add_argument(
        "--all",
        action="store_true",
        help="Ingest docs for all crosswalks in store",
    )
    ingest_api.add_argument(
        "--sssom-dir",
        default="exports/sssom",
        help="Directory where .sssom.tsv files are written",
    )

    bootstrap = sub.add_parser(
        "bootstrap-rdamsc",
        help="Sync RDAMSC catalog and generate SSSOM files for missing mappings",
    )
    bootstrap.add_argument(
        "--sssom-dir",
        default="exports/sssom",
        help="Directory where .sssom.tsv files are written",
    )
    bootstrap.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest even when SSSOM file already exists",
    )
    bootstrap.add_argument(
        "--crosswalk-id",
        default="",
        help="Run bootstrap only for one crosswalk id",
    )
    bootstrap.add_argument(
        "--verbose",
        action="store_true",
        help="Print step-by-step pipeline logs",
    )

    sub.add_parser("demo-convert", help="Run fast synthetic conversion")
    sub.add_parser(
        "benchmark-fixture", help="Run fast fixture benchmark and print JSON"
    )
    return parser


def _default_mapping_pdf() -> Path:
    return Path("/home/casas/AI/Metadata-Mappings/DataCite_DublinCore_Mapping.pdf")


def _load_demo_bundle(store):
    pdf_path = _default_mapping_pdf()
    if not pdf_path.exists():
        print("error: expected mapping PDF missing")
        return None
    crosswalk_id = ingest_datacite_to_dc_pdf(store, pdf_path)
    bundle = store.get_crosswalk_bundle(crosswalk_id)
    if bundle is None:
        print("error: crosswalk bundle missing")
        return None
    _ = ensure_sssom_for_bundle(bundle, Path("exports/sssom"))
    return bundle


def _logger_from_verbose(verbose: bool) -> Callable[[str], None] | None:
    if not verbose:
        return None

    def _logger(message: str) -> None:
        print(message, flush=True)

    return _logger


def _targets_for_ingest(store, args: argparse.Namespace) -> list[str] | None:
    crosswalks = store.list_crosswalks()
    if not crosswalks:
        _ = sync_rdamsc_catalog(store)
        crosswalks = store.list_crosswalks()

    if args.all:
        return [x.id for x in crosswalks]
    if args.crosswalk_id:
        if not any(x.id == args.crosswalk_id for x in crosswalks):
            _ = sync_rdamsc_catalog(store)
        return [args.crosswalk_id]

    print("error: provide --crosswalk-id or --all")
    return None


def _cmd_ingest_pdf(store, args: argparse.Namespace) -> int:
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"error: pdf not found: {pdf_path}")
        return 2
    crosswalk_id = ingest_datacite_to_dc_pdf(store, pdf_path)
    bundle = store.get_crosswalk_bundle(crosswalk_id)
    count = len(bundle.rules) if bundle else 0
    if bundle is not None:
        _ = ensure_sssom_for_bundle(bundle, Path("exports/sssom"))
    print(json.dumps({"crosswalk_id": crosswalk_id, "rules": count}))
    return 0


def _cmd_sync_rdamsc(store, args: argparse.Namespace) -> int:
    count = sync_rdamsc_catalog(store)
    result: dict[str, object] = {"synced": count}
    if args.with_ingest:
        out_dir = Path(args.sssom_dir)
        outputs: list[IngestResult] = []
        for crosswalk in store.list_crosswalks():
            outputs.append(ingest_rdamsc_crosswalk_docs(store, crosswalk.id, out_dir))
        result["ingest_results"] = outputs
    print(dump_result_json(result))
    return 0


def _cmd_ingest_rdamsc(store, args: argparse.Namespace) -> int:
    targets = _targets_for_ingest(store, args)
    if targets is None:
        return 2

    out_dir = Path(args.sssom_dir)
    outputs: list[IngestResult] = [
        ingest_rdamsc_crosswalk_docs(store, cid, out_dir) for cid in targets
    ]
    print(dump_result_json({"results": outputs}))
    return 0


def _cmd_bootstrap_rdamsc(store, args: argparse.Namespace) -> int:
    result: BootstrapPipelineResult = run_bootstrap_pipeline(
        store,
        Path(args.sssom_dir),
        force=bool(args.force),
        only_crosswalk_id=(args.crosswalk_id or None),
        logger=_logger_from_verbose(bool(args.verbose)),
    )
    print(dump_result_json(result))
    return 0


def _cmd_demo_convert(store, _args: argparse.Namespace) -> int:
    bundle = _load_demo_bundle(store)
    if bundle is None:
        return 2

    source_ir: dict[str, list[IRValue]] = {}
    add_ir_value(source_ir, "publicationYear", IRValue(text="2024"))
    add_ir_value(source_ir, "Identifier", IRValue(text="10.1000/demo"))
    target_ir, report = apply_mapping_rules(source_ir, bundle.rules)
    xml = ir_to_dublin_core_xml(target_ir)
    print(
        json.dumps(
            {
                "applied_rules": len(report.applied_rule_ids),
                "unmapped": len(report.unmapped_fields),
                "xml_preview": xml[:180],
            }
        )
    )
    return 0


def _cmd_benchmark_fixture(store, _args: argparse.Namespace) -> int:
    bundle = _load_demo_bundle(store)
    if bundle is None:
        return 2

    source_xml = (
        "<oaire:resource xmlns:oaire='http://namespace.openaire.eu/schema/oaire/' "
        "xmlns:datacite='http://datacite.org/schema/kernel-4'>"
        "<datacite:titles><datacite:title>Demo title</datacite:title></datacite:titles>"
        "<datacite:creators><datacite:creator><datacite:creatorName>Doe, Jane</datacite:creatorName></datacite:creator></datacite:creators>"
        "<datacite:identifier>10.000/demo</datacite:identifier>"
        "</oaire:resource>"
    )
    expected_dc = "title: Demo title\ncreator: Doe, Jane\nidentifier: 10.000/demo\n"
    summary = run_fixture_benchmark(bundle, source_xml, expected_dc, n_cases=1)
    print(benchmark_summary_to_json(summary))
    return 0


def run_cli(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    store = build_default_store()
    handlers: dict[str, Callable[[object, argparse.Namespace], int]] = {
        "ingest-pdf": _cmd_ingest_pdf,
        "sync-rdamsc": _cmd_sync_rdamsc,
        "ingest-rdamsc": _cmd_ingest_rdamsc,
        "bootstrap-rdamsc": _cmd_bootstrap_rdamsc,
        "demo-convert": _cmd_demo_convert,
        "benchmark-fixture": _cmd_benchmark_fixture,
    }
    handler = handlers.get(args.command)
    if handler is None:
        print("error: unsupported command")
        return 2
    return handler(store, args)


def main() -> None:
    import sys

    raise SystemExit(run_cli(sys.argv[1:]))


if __name__ == "__main__":
    main()
