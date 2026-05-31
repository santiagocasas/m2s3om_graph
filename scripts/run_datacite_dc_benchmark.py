"""Run a real DataCite/OpenAIRE to Dublin Core benchmark over distinct records."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from defusedxml import ElementTree as ET

from m2s3om_graph.benchmark.metrics import compare_ir_detailed
from m2s3om_graph.benchmark.report import benchmark_summary_to_csv, benchmark_summary_to_json
from m2s3om_graph.benchmark.runner import BenchmarkCase, BenchmarkSummary, run_elib_benchmark
from m2s3om_graph.db import InMemoryCrosswalkStore
from m2s3om_graph.ingest.crosswalk_ingestion import ingest_datacite_to_dc_pdf
from m2s3om_graph.interop.elib import parse_openaire_xml_to_ir
from m2s3om_graph.oai.client import OAIClient
from m2s3om_graph.oai.parser import parse_identifiers
from m2s3om_graph.oai.registry import load_institution_endpoints
from m2s3om_graph.transform.apply import apply_mapping_rules
from m2s3om_graph.transform.ir import IRRecord, IRValue, add_ir_value
from m2s3om_graph.transform.parsers import parse_oai_dc_xml_to_ir


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PDF = Path("/home/casas/AI/Metadata-Mappings/DataCite_DublinCore_Mapping.pdf")
DEFAULT_OUTPUT_DIR = ROOT / "exports" / "benchmark"
OAI_NS = {"oai": "http://www.openarchives.org/OAI/2.0/"}
DC_ALIAS_KEYS: dict[str, list[str]] = {
    "title": ["Title", "title"],
    "creator": ["Creator", "creatorName"],
    "identifier": ["Identifier", "identifier"],
    "date": ["Date"],
    "subject": ["subject"],
    "relation": ["relatedIdentifier"],
}


def _load_bundle(pdf_path: Path):
    store = InMemoryCrosswalkStore()
    crosswalk_id = ingest_datacite_to_dc_pdf(store, pdf_path)
    bundle = store.get_crosswalk_bundle(crosswalk_id)
    if bundle is None:
        raise RuntimeError(f"failed to load crosswalk from {pdf_path}")
    return bundle


def _write_outputs(summary: BenchmarkSummary, output_dir: Path, stem: str) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"{stem}.json").write_text(
        benchmark_summary_to_json(summary), encoding="utf-8"
    )


def _parse_oai_dc_expected_ir(xml_text: str) -> IRRecord:
    raw_ir = parse_oai_dc_xml_to_ir(xml_text)
    expected_ir: IRRecord = {}
    for key, values in raw_ir.items():
        if ":" not in key:
            continue
        _prefix, local_name = key.split(":", 1)
        target_key = f"dcterms:{local_name}"
        for value in values:
            add_ir_value(expected_ir, target_key, value)
            for alias in DC_ALIAS_KEYS.get(local_name.lower(), []):
                add_ir_value(expected_ir, alias, IRValue(text=value.text))
            if local_name.lower() == "date" and len(value.text) >= 4 and value.text[:4].isdigit():
                add_ir_value(expected_ir, "publicationYear", IRValue(text=value.text[:4]))
    return expected_ir


def _raise_for_oai_error(xml_text: str, *, record_id: str, metadata_prefix: str) -> None:
    root = ET.fromstring(xml_text)
    error = root.find(".//oai:error", OAI_NS)
    if error is None:
        return
    code = error.attrib.get("code", "unknown")
    message = (error.text or "").strip()
    raise RuntimeError(f"{record_id} {metadata_prefix}: OAI error {code}: {message}")
    (output_dir / f"{stem}.csv").write_text(
        benchmark_summary_to_csv(summary), encoding="utf-8"
    )


def _run_oai_pair_benchmark(
    *,
    endpoint: str,
    record_ids: list[str],
    limit: int,
    timeout_s: int,
    crosswalk,
) -> tuple[BenchmarkSummary, list[dict[str, str]]]:
    client = OAIClient(endpoint, timeout_s=timeout_s)
    cases: list[BenchmarkCase] = []
    failures: list[dict[str, str]] = []

    for record_id in record_ids:
        if len(cases) >= limit:
            break
        try:
            openaire_xml = client.get_record(record_id, metadata_prefix="oai_openaire")
            dc_xml = client.get_record(record_id, metadata_prefix="oai_dc")
            _raise_for_oai_error(
                openaire_xml, record_id=record_id, metadata_prefix="oai_openaire"
            )
            _raise_for_oai_error(dc_xml, record_id=record_id, metadata_prefix="oai_dc")
            source_ir = parse_openaire_xml_to_ir(openaire_xml)
            expected_ir = _parse_oai_dc_expected_ir(dc_xml)
            actual_ir, report = apply_mapping_rules(source_ir, crosswalk.rules)
            metrics, diffs, confusion = compare_ir_detailed(
                actual_ir,
                expected_ir,
                semantic_loss_rules=len(report.semantic_loss_rules),
                total_rules=len(crosswalk.rules),
            )
            cases.append(
                BenchmarkCase(
                    case_id=record_id,
                    direction="oai_openaire_to_oai_dc",
                    metrics=metrics,
                    field_diffs=diffs,
                    confusion_matrix=confusion,
                    unmapped_fields=report.unmapped_fields,
                )
            )
        except Exception as exc:  # noqa: BLE001 - benchmark should keep sampling.
            failures.append({"record_id": record_id, "error": str(exc)})

    return BenchmarkSummary(cases=cases), failures


def _discover_oai_ids(endpoint: str, *, limit: int, timeout_s: int) -> list[str]:
    client = OAIClient(endpoint, timeout_s=timeout_s)
    xml_text = client.list_identifiers(metadata_prefix="oai_openaire")
    parsed = parse_identifiers(xml_text, limit=limit)
    identifiers = list(parsed.identifiers)
    token = parsed.resumption_token
    while token and len(identifiers) < limit:
        xml_text = client.list_identifiers_resumption(token)
        parsed = parse_identifiers(xml_text, limit=limit - len(identifiers))
        identifiers.extend(parsed.identifiers)
        token = parsed.resumption_token
    return identifiers[:limit]


def _institution_endpoint(name: str) -> str:
    for item in load_institution_endpoints():
        if item.name.lower() == name.lower():
            return item.oai_endpoint
    raise ValueError(f"unknown institution endpoint: {name}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["elib", "oai"], default="elib")
    parser.add_argument("--institution", default="DLR")
    parser.add_argument("--endpoint", default="")
    parser.add_argument("--record-id", action="append", default=[])
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    bundle = _load_bundle(args.pdf)

    failures: list[dict[str, str]] = []
    if args.mode == "elib":
        if not args.record_id:
            raise SystemExit("--record-id is required for --mode elib")
        summary = run_elib_benchmark(bundle, args.record_id[: args.limit])
        stem = "datacite_dc_elib_benchmark"
    else:
        endpoint = args.endpoint or _institution_endpoint(args.institution)
        record_ids = args.record_id
        if args.discover:
            record_ids = _discover_oai_ids(endpoint, limit=args.limit * 3, timeout_s=args.timeout)
        if not record_ids:
            raise SystemExit("provide --record-id or --discover for --mode oai")
        summary, failures = _run_oai_pair_benchmark(
            endpoint=endpoint,
            record_ids=record_ids,
            limit=args.limit,
            timeout_s=args.timeout,
            crosswalk=bundle,
        )
        stem = f"datacite_dc_oai_{args.institution.lower()}_benchmark"

    _write_outputs(summary, args.output_dir, stem)
    if failures:
        (args.output_dir / f"{stem}.failures.json").write_text(
            json.dumps(failures, indent=2), encoding="utf-8"
        )

    print(
        json.dumps(
            {
                "cases": len(summary.cases),
                "avg_field_coverage": summary.avg_field_coverage,
                "avg_value_overlap": summary.avg_value_overlap,
                "avg_semantic_loss_rate": summary.avg_semantic_loss_rate,
                "failures": len(failures),
                "output_dir": str(args.output_dir),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
