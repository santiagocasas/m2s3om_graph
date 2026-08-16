from pathlib import Path
import re


SPACE_ROOT = Path(__file__).resolve().parents[1] / "spaces" / "m2s3om-streamlit-space"
PY_FILE_PATTERNS = {".py"}
TEXT_FILE_NAMES = {"Dockerfile", "requirements.txt", "README.md"}
CORE_PACKAGES = (
    "streamlit",
    "surrealdb",
    "pydantic",
    "pypdf",
    "requests",
    "pyyaml",
    "matplotlib",
)


def _iter_scaffold_files() -> list[Path]:
    files: list[Path] = []
    for path in SPACE_ROOT.rglob("*"):
        if path.is_file() and (path.suffix in PY_FILE_PATTERNS or path.name in TEXT_FILE_NAMES):
            files.append(path)
    return sorted(files)


def _strip_python_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not re.match(r"^\s*#", line))


def test_scaffold_structure_exists() -> None:
    assert (SPACE_ROOT / "Dockerfile").is_file()
    assert (SPACE_ROOT / "requirements.txt").is_file()
    assert (SPACE_ROOT / "README.md").is_file()
    assert (SPACE_ROOT / "app" / "app.py").is_file()
    assert (SPACE_ROOT / "src" / "m2s3om_graph" / "__init__.py").is_file()
    assert (SPACE_ROOT / "exports" / "sssom").is_dir()


def test_dockerfile_uses_expected_runtime_contract() -> None:
    text = (SPACE_ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert text.startswith("FROM python:3.12-slim")
    assert "--server.port=7860" in text
    assert "--server.address=0.0.0.0" in text


def test_requirements_contains_core_pins() -> None:
    text = (SPACE_ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert text.strip()
    for package in CORE_PACKAGES:
        assert re.search(rf"^{re.escape(package)}(==|>=|~=)", text, re.MULTILINE), package


def test_scaffold_contains_no_claude_suggestions_token() -> None:
    for path in _iter_scaffold_files():
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".py":
            text = _strip_python_comments(text)
        assert re.search(r"claude_suggestions", text) is None, path


def test_scaffold_surrealdb_defaults_are_env_guarded() -> None:
    for path in sorted(SPACE_ROOT.rglob("*.py")):
        text = _strip_python_comments(path.read_text(encoding="utf-8"))
        for needle in ("ws://localhost", "http://localhost:8000"):
            for match in re.finditer(re.escape(needle), text):
                window_start = max(0, match.start() - 200)
                assert "os.getenv(" in text[window_start:match.start()], (path, needle)
