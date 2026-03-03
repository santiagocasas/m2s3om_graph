import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from markitdown import MarkItDown
from pypdf import PdfReader

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
}


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if text:
            self.parts.append(text)

    def text(self) -> str:
        return "\n".join(self.parts)


@dataclass
class ArtifactText:
    url: str
    content_type: str
    text: str


_MARKITDOWN = MarkItDown(enable_plugins=False)


class ArtifactFetchError(RuntimeError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        reason: str = "fetch_error",
    ):
        super().__init__(message)
        self.status_code = status_code
        self.reason = reason


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _is_pdf_url(url: str) -> bool:
    return urlparse(url).path.lower().endswith(".pdf")


def _is_html_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    if path.endswith(".html") or path.endswith(".htm"):
        return True
    return "." not in path.split("/")[-1]


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = _normalize_text("\n".join(pages))
    return _normalize_text(_normalize_legacy_shifted_text(text))


def _normalize_legacy_shifted_text(text: str) -> str:
    if not text:
        return text
    total = len(text)
    lower_ratio = sum(ch.islower() for ch in text) / total
    upper_ratio = sum(ch.isupper() for ch in text) / total
    control_ratio = sum(ord(ch) < 32 and ch not in "\n\r\t" for ch in text) / total

    if not (lower_ratio < 0.03 and upper_ratio > 0.35 and control_ratio > 0.08):
        return text

    decoded: list[str] = []
    for ch in text:
        code = ord(ch)
        if 33 <= code <= 96:
            decoded.append(chr(code + 29))
        elif code < 32 and ch not in "\n\r\t":
            decoded.append(" ")
        else:
            decoded.append(ch)

    normalized = "".join(decoded)
    normalized = normalized.replace("’", "D").replace("‘", "D")
    normalized = normalized.replace("¶", "'")
    return normalized


def _extract_html_text(content: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(content)
    return _normalize_text(parser.text())


def _markitdown_convert(content: bytes, *, url: str) -> str:
    ext = artifact_extension(url)
    file_extension = None if ext == "(none)" else ext
    result = _MARKITDOWN.convert_stream(
        BytesIO(content),
        file_extension=file_extension,
        url=url,
    )
    markdown = result.markdown or result.text_content or ""
    normalized = _normalize_text(markdown)
    if ext == ".pdf":
        normalized = _normalize_text(_normalize_legacy_shifted_text(normalized))
    return normalized


def _soffice_binary() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def _convert_legacy_doc_via_soffice(content: bytes, *, url: str) -> str:
    binary = _soffice_binary()
    if not binary:
        raise RuntimeError(
            "Legacy .doc conversion needs LibreOffice (soffice/libreoffice) installed"
        )

    with tempfile.TemporaryDirectory(prefix="kaigraph_doc_convert_") as tmp_dir:
        tmp_path = Path(tmp_dir)
        source_path = tmp_path / "input.doc"
        out_dir = tmp_path / "out"
        out_dir.mkdir(parents=True, exist_ok=True)
        source_path.write_bytes(content)

        cmd = [
            binary,
            "--headless",
            "--convert-to",
            "docx",
            "--outdir",
            str(out_dir),
            str(source_path),
        ]
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "LibreOffice conversion failed: "
                + (
                    completed.stderr.strip()
                    or completed.stdout.strip()
                    or "unknown error"
                )
            )

        converted = out_dir / "input.docx"
        if not converted.exists():
            candidates = sorted(out_dir.glob("*.docx"))
            if not candidates:
                raise RuntimeError("LibreOffice conversion produced no DOCX output")
            converted = candidates[0]

        return _markitdown_convert(converted.read_bytes(), url=url + ".docx")


def artifact_extension(url: str) -> str:
    suffix = urlparse(url).path.rsplit("/", 1)[-1]
    if "." not in suffix:
        return "(none)"
    return "." + suffix.split(".")[-1].lower()


def _github_raw_fallback(url: str) -> str | None:
    parsed = urlparse(url)
    if parsed.netloc != "github.com":
        return None
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 5:
        return None
    owner, repo, marker = parts[0], parts[1], parts[2]
    if marker != "raw":
        return None
    branch = parts[3]
    tail = "/".join(parts[4:])
    return f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{tail}"


def _candidate_urls(url: str) -> list[str]:
    out = [url]
    fallback = _github_raw_fallback(url)
    if fallback and fallback not in out:
        out.append(fallback)
    if url.startswith("http://"):
        https = "https://" + url[len("http://") :]
        if https not in out:
            out.append(https)
    return out


def fetch_artifact_text(
    url: str, timeout: int = 30, max_chars: int = 200_000
) -> ArtifactText:
    errors: list[str] = []
    for candidate in _candidate_urls(url):
        try:
            response = requests.get(candidate, timeout=timeout, headers=DEFAULT_HEADERS)
            response.raise_for_status()
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else None
            errors.append(f"{candidate} -> HTTP {code}")
            continue
        except requests.RequestException as exc:
            errors.append(f"{candidate} -> {exc}")
            continue

        content_type = (response.headers.get("content-type") or "").lower()
        try:
            text = _markitdown_convert(response.content, url=candidate)
        except Exception as exc:
            is_pdf = "application/pdf" in content_type or _is_pdf_url(candidate)
            is_html = "text/html" in content_type or _is_html_url(candidate)
            is_doc = artifact_extension(candidate) == ".doc"
            is_text_like = any(
                x in content_type
                for x in (
                    "text/plain",
                    "application/xml",
                    "text/xml",
                    "application/xslt+xml",
                )
            )

            if is_pdf:
                text = _extract_pdf_text(response.content)
            elif is_html:
                text = _extract_html_text(response.text)
            elif is_doc:
                try:
                    text = _convert_legacy_doc_via_soffice(
                        response.content, url=candidate
                    )
                except Exception as doc_exc:
                    raise ArtifactFetchError(
                        f"{candidate} -> Legacy .doc conversion failed: {doc_exc}",
                        reason="conversion_error",
                    ) from doc_exc
            elif is_text_like:
                text = _normalize_text(response.text)
            else:
                raise ArtifactFetchError(
                    f"{candidate} -> MarkItDown conversion failed: {exc}. "
                    "If this is legacy .doc, install LibreOffice or convert to .docx/.rtf first.",
                    reason="conversion_error",
                )

        if len(text) > max_chars:
            text = text[:max_chars]

        return ArtifactText(
            url=candidate,
            content_type=content_type or "text/plain",
            text=text,
        )

    error_text = "; ".join(errors) if errors else f"Failed to fetch {url}"
    raise ArtifactFetchError(error_text, reason="fetch_error")


def is_easy_supported_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    easy = (
        ".pdf",
        ".html",
        ".htm",
        ".txt",
        ".xml",
        ".xsl",
        ".xslt",
    )
    if path.endswith(easy):
        return True
    return "." not in path.split("/")[-1]
