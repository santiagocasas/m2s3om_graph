import argparse
import json
from pathlib import Path
from typing import Callable

from kaigraph.benchmark import benchmark_summary_to_json, run_fixture_benchmark
from kaigraph.db import build_default_store
from kaigraph.ingest import ingest_datacite_to_dc_pdf
from kaigraph.rdamsc import (
    dump_result_json,
    ensure_sssom_for_bundle,
    ingest_rdamsc_crosswalk_docs,
    run_bootstrap_pipeline,
    sync_rdamsc_catalog,
)
from kaigraph.transform import (
    IRValue,
    add_ir_value,
    apply_mapping_rules,
    ir_to_dublin_core_xml,
)


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


def run_cli(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    store = build_default_store()

    if args.command == "ingest-pdf":
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

    if args.command == "sync-rdamsc":
        count = sync_rdamsc_catalog(store)
        result: dict[str, object] = {"synced": count}
        if args.with_ingest:
            out_dir = Path(args.sssom_dir)
            outputs: list[dict[str, object]] = []
            for crosswalk in store.list_crosswalks():
                outputs.append(
                    ingest_rdamsc_crosswalk_docs(store, crosswalk.id, out_dir)
                )
            result["ingest_results"] = outputs
        print(dump_result_json(result))
        return 0

    if args.command == "ingest-rdamsc":
        out_dir = Path(args.sssom_dir)
        if not store.list_crosswalks():
            _ = sync_rdamsc_catalog(store)
        targets: list[str] = []
        if args.all:
            targets = [x.id for x in store.list_crosswalks()]
        elif args.crosswalk_id:
            if not any(x.id == args.crosswalk_id for x in store.list_crosswalks()):
                _ = sync_rdamsc_catalog(store)
            targets = [args.crosswalk_id]
        else:
            print("error: provide --crosswalk-id or --all")
            return 2

        outputs = [ingest_rdamsc_crosswalk_docs(store, cid, out_dir) for cid in targets]
        print(dump_result_json({"results": outputs}))
        return 0

    if args.command == "bootstrap-rdamsc":
        out_dir = Path(args.sssom_dir)
        logger_fn: Callable[[str], None] | None = None
        if args.verbose:

            def _logger(message: str) -> None:
                print(message, flush=True)

            logger_fn = _logger

        result = run_bootstrap_pipeline(
            store,
            out_dir,
            force=bool(args.force),
            only_crosswalk_id=(args.crosswalk_id or None),
            logger=logger_fn,
        )
        print(dump_result_json(result))
        return 0

    if args.command == "demo-convert":
        pdf_path = Path(
            "/home/casas/AI/Metadata-Mappings/DataCite_DublinCore_Mapping.pdf"
        )
        if not pdf_path.exists():
            print("error: expected mapping PDF missing")
            return 2
        crosswalk_id = ingest_datacite_to_dc_pdf(store, pdf_path)
        bundle = store.get_crosswalk_bundle(crosswalk_id)
        if bundle is None:
            print("error: crosswalk bundle missing")
            return 2
        _ = ensure_sssom_for_bundle(bundle, Path("exports/sssom"))

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

    if args.command == "benchmark-fixture":
        pdf_path = Path(
            "/home/casas/AI/Metadata-Mappings/DataCite_DublinCore_Mapping.pdf"
        )
        if not pdf_path.exists():
            print("error: expected mapping PDF missing")
            return 2
        crosswalk_id = ingest_datacite_to_dc_pdf(store, pdf_path)
        bundle = store.get_crosswalk_bundle(crosswalk_id)
        if bundle is None:
            print("error: crosswalk bundle missing")
            return 2
        _ = ensure_sssom_for_bundle(bundle, Path("exports/sssom"))

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

    print("error: unsupported command")
    return 2


def main() -> None:
    import sys

    raise SystemExit(run_cli(sys.argv[1:]))


if __name__ == "__main__":
    main()
