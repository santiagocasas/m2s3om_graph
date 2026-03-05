from dataclasses import dataclass, field

from kaigraph.db import MappingType


@dataclass(frozen=True)
class DeterministicCandidate:
    source_path: str
    target_path: str
    mapping_type: MappingType
    confidence: float
    notes: str | None = None
    evidence: str | None = None
    extractor_name: str = "unknown"

    def to_record(self) -> dict[str, object]:
        return {
            "source_path": self.source_path,
            "target_path": self.target_path,
            "mapping_type": self.mapping_type.value,
            "confidence": self.confidence,
            "notes": self.notes,
            "evidence": self.evidence,
        }


@dataclass
class DeterministicDiagnostics:
    total_chars: int
    normalized_chars: int
    total_lines: int
    extractor_counts: dict[str, int] = field(default_factory=dict)
    candidates_before_dedupe: int = 0
    candidates_after_dedupe: int = 0

    def to_record(self) -> dict[str, object]:
        return {
            "total_chars": self.total_chars,
            "normalized_chars": self.normalized_chars,
            "total_lines": self.total_lines,
            "extractor_counts": dict(self.extractor_counts),
            "candidates_before_dedupe": self.candidates_before_dedupe,
            "candidates_after_dedupe": self.candidates_after_dedupe,
        }
