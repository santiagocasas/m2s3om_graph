from .extractors import extract_assignment_candidates, extract_markdown_table_candidates
from .normalizers import normalize_text_for_deterministic
from .types import DeterministicCandidate, DeterministicDiagnostics


def _dedupe_key(candidate: DeterministicCandidate) -> tuple[str, str, str]:
    return (
        candidate.source_path.strip().lower(),
        candidate.target_path.strip().lower(),
        candidate.mapping_type.value,
    )


def extract_deterministic_candidates(
    text: str,
    *,
    max_rules: int = 160,
) -> tuple[list[DeterministicCandidate], DeterministicDiagnostics]:
    normalized = normalize_text_for_deterministic(text)
    diagnostics = DeterministicDiagnostics(
        total_chars=len(text),
        normalized_chars=len(normalized),
        total_lines=len(normalized.splitlines()),
    )

    extractor_outputs: list[tuple[str, list[DeterministicCandidate]]] = [
        ("assignment", extract_assignment_candidates(normalized)),
        ("markdown_table", extract_markdown_table_candidates(normalized)),
    ]

    combined: list[DeterministicCandidate] = []
    for name, values in extractor_outputs:
        diagnostics.extractor_counts[name] = len(values)
        combined.extend(values)

    diagnostics.candidates_before_dedupe = len(combined)

    out: list[DeterministicCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    for candidate in combined:
        if len(out) >= max_rules:
            break
        key = _dedupe_key(candidate)
        if key in seen:
            continue
        seen.add(key)
        out.append(candidate)

    diagnostics.candidates_after_dedupe = len(out)
    return out, diagnostics
