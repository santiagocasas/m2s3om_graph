import re

from kaigraph.db import MappingType

from .types import DeterministicCandidate

_ASSIGNMENT_RE = re.compile(
    r"^(?P<src>[A-Za-z][A-Za-z0-9_.:@/\-]{0,80})\s*(?P<op>=|->|=>)\s*(?P<tgt>.+)$"
)


def _clean_value(value: str) -> str:
    cleaned = value.strip().strip("|;,.:-")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned


def _looks_like_source(value: str) -> bool:
    if not value:
        return False
    if " " in value:
        return False
    return bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_.:@/\-]{0,80}", value))


def _looks_like_target(value: str) -> bool:
    if not value:
        return False
    if len(value) > 240:
        return False
    return (
        ":" in value
        or "." in value
        or bool(re.search(r"\bE\d{1,3}\b", value))
        or bool(re.search(r"\b[A-Z]{2,}[A-Za-z0-9\-]*\b", value))
    )


def _mapping_type_for_line(source: str, target: str, line: str) -> MappingType:
    lowered = line.lower()
    target_lower = target.lower()
    if "not present" in target_lower:
        return MappingType.MISSING
    if "is composed of" in lowered or "concatenate" in lowered:
        return MappingType.AGGREGATION
    if "(join)" in lowered or (" has " in lowered and ":" in line):
        return MappingType.DECOMPOSITION
    if "@" in source:
        return MappingType.CONDITIONAL
    return MappingType.DIRECT


def _confidence_for_type(mapping_type: MappingType) -> float:
    if mapping_type in {MappingType.DIRECT, MappingType.MISSING}:
        return 0.9
    if mapping_type == MappingType.DECOMPOSITION:
        return 0.84
    if mapping_type == MappingType.AGGREGATION:
        return 0.82
    return 0.8


def extract_assignment_candidates(text: str) -> list[DeterministicCandidate]:
    out: list[DeterministicCandidate] = []
    for line in text.splitlines():
        match = _ASSIGNMENT_RE.match(line)
        if match is None:
            continue
        source = _clean_value(match.group("src"))
        target = _clean_value(match.group("tgt"))
        if not _looks_like_source(source):
            continue
        if not _looks_like_target(target):
            continue

        mapping_type = _mapping_type_for_line(source, target, line)
        out.append(
            DeterministicCandidate(
                source_path=source,
                target_path=target,
                mapping_type=mapping_type,
                confidence=_confidence_for_type(mapping_type),
                notes="Deterministic assignment-pattern extraction.",
                evidence=line[:400],
                extractor_name="assignment",
            )
        )
    return out


def extract_markdown_table_candidates(text: str) -> list[DeterministicCandidate]:
    out: list[DeterministicCandidate] = []
    lines = text.splitlines()
    for line in lines:
        if not line.startswith("|"):
            continue
        parts = [x.strip() for x in line.strip().strip("|").split("|")]
        if len(parts) < 2:
            continue
        if all(set(part) <= {"-", " ", ":"} for part in parts):
            continue
        source = _clean_value(parts[0])
        target = _clean_value(parts[1])
        if not source or not target:
            continue
        if not _looks_like_target(target):
            continue
        mapping_type = MappingType.CONDITIONAL if "@" in source else MappingType.DIRECT
        out.append(
            DeterministicCandidate(
                source_path=source,
                target_path=target,
                mapping_type=mapping_type,
                confidence=0.78,
                notes="Deterministic markdown-table extraction.",
                evidence=line[:400],
                extractor_name="markdown_table",
            )
        )
    return out
