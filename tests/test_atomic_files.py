from pathlib import Path

from kaigraph.atomic_files import atomic_write_text


def test_atomic_write_text_creates_file(tmp_path: Path) -> None:
    target = tmp_path / "status.json"
    atomic_write_text(target, "one")
    assert target.read_text(encoding="utf-8") == "one"


def test_atomic_write_text_overwrites_existing_file(tmp_path: Path) -> None:
    target = tmp_path / "status.json"
    target.write_text("old", encoding="utf-8")

    atomic_write_text(target, "new")
    assert target.read_text(encoding="utf-8") == "new"
