from pathlib import Path

from m2s3om_graph.cli.main import run_cli


def test_cli_demo_convert_fast() -> None:
    code = run_cli(["demo-convert"])
    assert code == 0


def test_cli_ingest_pdf_path_validation() -> None:
    missing = Path("/tmp/does_not_exist_crosswalk.pdf")
    code = run_cli(["ingest-pdf", "--pdf", str(missing)])
    assert code == 2


def test_cli_benchmark_fixture_fast() -> None:
    code = run_cli(["benchmark-fixture"])
    assert code == 0
