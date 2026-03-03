import math
import re
from dataclasses import dataclass

from kaigraph.db import CrosswalkRepository
from kaigraph.models import Chunk, Element

WORD_RE = re.compile(r"[A-Za-z0-9_]+")


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in WORD_RE.findall(text)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


@dataclass
class RetrievedEvidence:
    chunk: Chunk
    score: float


def retrieve_for_element(
    repo: CrosswalkRepository,
    query_element: Element,
    target_standard_id: str,
    top_k: int = 6,
) -> list[RetrievedEvidence]:
    query_tokens = _tokens(f"{query_element.label} {query_element.scope_note or ''}")
    target_elements = repo.list_elements(target_standard_id)
    target_ids = {x.id for x in target_elements}

    ranked: list[RetrievedEvidence] = []
    for chunk in repo.all_chunks():
        chunk_tokens = _tokens(chunk.content)
        lexical = jaccard(query_tokens, chunk_tokens)
        node_bonus = 0.1 if chunk.element_id in target_ids else 0.0
        score = min(1.0, lexical + node_bonus)
        if score <= 0:
            continue
        ranked.append(RetrievedEvidence(chunk=chunk, score=score))
    ranked.sort(key=lambda x: (-x.score, x.chunk.id))
    return ranked[:top_k]


def confidence_from_similarity(similarity: float, penalties: int = 0) -> float:
    value = similarity - (penalties * 0.1)
    return max(0.0, min(1.0, value))


def cosine_like(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / math.sqrt(len(a) * len(b))
