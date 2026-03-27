import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

from kaigraph.db import MappingType

ID_RE = re.compile(r"^(\d+(?:\.\d+)*(?:\.[a-z])?)\s+(.*)$", re.IGNORECASE)
TERM_RE = re.compile(r"(dcterms:[A-Za-z][A-Za-z0-9]+)$")


@dataclass
class ParsedCase:
    key: str
    value: str


@dataclass
class ParsedMappingRow:
    row_id: str
    datacite_property: str
    dublin_core: str
    page_number: int
    snippet: str
    mapping_type: MappingType
    notes: str | None = None
    cases: list[ParsedCase] = field(default_factory=list)


def _normalize_spaces(text: str) -> str:
    return " ".join(text.replace("\u2010", "-").replace("\u2011", "-").split())


def _split_property_and_target(rest: str) -> tuple[str, str] | None:
    lowered = rest.lower()
    marker = "not present in dublin core"
    if marker in lowered:
        idx = lowered.find(marker)
        return _normalize_spaces(rest[:idx]), "Not present in Dublin Core"

    if "dcterms:" in rest:
        idx = rest.rfind("dcterms:")
        return _normalize_spaces(rest[:idx]), _normalize_spaces(rest[idx:])
    return None


def _parse_id_row(line: str, page_number: int) -> ParsedMappingRow | None:
    match = ID_RE.match(line)
    if not match:
        return None
    row_id = match.group(1)
    rest = _normalize_spaces(match.group(2))
    if not rest or rest.lower().startswith("datacite-property"):
        return None

    split = _split_property_and_target(rest)
    if split is None:
        # Row with narrative only; keep placeholder target.
        return ParsedMappingRow(
            row_id=row_id,
            datacite_property=rest,
            dublin_core="",
            page_number=page_number,
            snippet=_normalize_spaces(line),
            mapping_type=MappingType.PASSTHROUGH,
            notes=rest,
        )

    property_name, dc_col = split
    if dc_col == "Not present in Dublin Core":
        mapping_type = MappingType.MISSING
    else:
        mapping_type = MappingType.DIRECT
    return ParsedMappingRow(
        row_id=row_id,
        datacite_property=property_name,
        dublin_core=dc_col,
        page_number=page_number,
        snippet=_normalize_spaces(line),
        mapping_type=mapping_type,
    )


def _is_ignored_line(line: str) -> bool:
    return line in {
        "ID DataCite-Property Dublin Core",
        "DataCite to Dublin Core Mapping 4.4",
    }


def _append_note(current: ParsedMappingRow, line: str) -> None:
    if current.notes is None:
        current.notes = line
        return
    current.notes = f"{current.notes} {line}"


def _apply_continuation_line(current: ParsedMappingRow, line: str) -> None:
    if "dcterms:" in line:
        term_match = TERM_RE.search(line)
        if term_match is None:
            return
        term = term_match.group(1)
        key = _normalize_spaces(line[: term_match.start()]).strip()
        if key:
            current.cases.append(ParsedCase(key=key, value=term))
            current.mapping_type = MappingType.CONDITIONAL
        return

    if "concatenate" in line.lower():
        current.mapping_type = MappingType.AGGREGATION
        _append_note(current, line)
        return

    _append_note(current, line)


def _finalize_row(row: ParsedMappingRow, doc_uri: str | None) -> None:
    if row.cases and row.mapping_type != MappingType.CONDITIONAL:
        row.mapping_type = MappingType.CONDITIONAL
    if (
        row.mapping_type == MappingType.DIRECT
        and row.datacite_property.lower() == "relateditem"
    ):
        row.mapping_type = MappingType.AGGREGATION
        row.notes = (
            row.notes or ""
        ) + " Concatenate related item details into citation."
    if row.mapping_type == MappingType.PASSTHROUGH and row.dublin_core:
        row.mapping_type = MappingType.DIRECT
    if doc_uri:
        row.snippet = f"[{doc_uri}] {row.snippet}"


def parse_mapping_page_texts(
    page_texts: list[str],
    doc_uri: str | None = None,
) -> list[ParsedMappingRow]:
    rows: list[ParsedMappingRow] = []
    current: ParsedMappingRow | None = None

    for page_number, raw_text in enumerate(page_texts, start=1):
        for raw_line in raw_text.splitlines():
            line = _normalize_spaces(raw_line)
            if not line or _is_ignored_line(line):
                continue

            parsed = _parse_id_row(line, page_number)
            if parsed is not None:
                rows.append(parsed)
                current = parsed
                continue

            if current is None:
                continue

            _apply_continuation_line(current, line)

    for row in rows:
        _finalize_row(row, doc_uri)

    return rows


def parse_mapping_pdf(
    pdf_path: str | Path, doc_uri: str | None = None
) -> list[ParsedMappingRow]:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(path)

    reader = PdfReader(str(path))
    page_texts = [(page.extract_text() or "") for page in reader.pages]
    return parse_mapping_page_texts(page_texts, doc_uri=doc_uri)
