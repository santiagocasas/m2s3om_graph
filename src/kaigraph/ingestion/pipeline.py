import hashlib
from dataclasses import dataclass

from kaigraph.db import CrosswalkRepository
from kaigraph.ingestion.extractor import extract_elements_from_text
from kaigraph.models import Chunk, Standard


def _chunk_text(text: str, max_chars: int = 900, overlap: int = 100) -> list[str]:
    cleaned = text.strip()
    if not cleaned:
        return []
    step = max_chars - overlap
    if step <= 0:
        step = max_chars
    out: list[str] = []
    for index in range(0, len(cleaned), step):
        part = cleaned[index : index + max_chars].strip()
        if part:
            out.append(part)
    return out


@dataclass
class StandardSource:
    standard: Standard
    text: str
    source_url: str | None = None


def ingest_standard_source(repo: CrosswalkRepository, source: StandardSource) -> None:
    repo.upsert_standard(source.standard)

    extraction = extract_elements_from_text(source.standard.id, source.text)
    repo.upsert_elements(extraction.elements)

    chunks: list[Chunk] = []
    for idx, part in enumerate(_chunk_text(source.text)):
        hash_id = hashlib.md5(
            f"{source.standard.id}:{idx}:{part}".encode("utf-8")
        ).hexdigest()
        chunks.append(
            Chunk(
                id=f"chunk:{hash_id}",
                standard_id=source.standard.id,
                content=part,
                source_url=source.source_url,
            )
        )
    repo.upsert_chunks(chunks)
