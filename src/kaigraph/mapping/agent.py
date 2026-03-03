from dataclasses import dataclass

from kaigraph.db import CrosswalkRepository
from kaigraph.models import Citation, Crosswalk, Element, MappingRecord
from kaigraph.retrieval.hybrid import (
    confidence_from_similarity,
    cosine_like,
    retrieve_for_element,
)


@dataclass
class MappingAgent:
    repo: CrosswalkRepository

    def generate_crosswalk(
        self,
        source_standard_id: str,
        target_standard_id: str,
    ) -> tuple[Crosswalk, list[MappingRecord]]:
        crosswalk = Crosswalk(
            id=f"crosswalk:{source_standard_id}:{target_standard_id}",
            source_standard_id=source_standard_id,
            target_standard_id=target_standard_id,
        )
        source_elements = self.repo.list_elements(source_standard_id)
        target_elements = self.repo.list_elements(target_standard_id)
        mappings: list[MappingRecord] = []
        for source in source_elements:
            candidate = self._best_target(source, target_elements)
            if candidate is None:
                continue
            target, similarity = candidate
            evidence = retrieve_for_element(
                self.repo, source, target_standard_id, top_k=3
            )
            citations = [
                Citation(
                    chunk_id=x.chunk.id,
                    url=x.chunk.source_url,
                    anchor=x.chunk.anchor,
                    snippet=x.chunk.content[:240],
                )
                for x in evidence
            ]
            hint = self._transformation_hint(source, target)
            ambiguity = similarity < 0.45
            semantic_loss = self._semantic_loss(source, target)
            confidence = confidence_from_similarity(
                similarity,
                penalties=int(ambiguity) + int(semantic_loss),
            )
            mappings.append(
                MappingRecord(
                    id=f"mapping:{source.id}->{target.id}",
                    crosswalk_id=crosswalk.id,
                    source_element_id=source.id,
                    target_element_id=target.id,
                    confidence=confidence,
                    justification=(
                        f"Mapped '{source.path}' to '{target.path}' based on lexical overlap "
                        f"and retrieved evidence snippets."
                    ),
                    transformation_hint=hint,
                    ambiguity_flag=ambiguity,
                    semantic_loss_flag=semantic_loss,
                    citations=citations,
                )
            )
        self.repo.save_crosswalk(crosswalk, mappings)
        return crosswalk, mappings

    def _best_target(
        self,
        source: Element,
        targets: list[Element],
    ) -> tuple[Element, float] | None:
        best: tuple[Element, float] | None = None
        source_tokens = set(
            (source.path + " " + (source.scope_note or "")).lower().split()
        )
        for target in targets:
            target_tokens = set(
                (target.path + " " + (target.scope_note or "")).lower().split()
            )
            similarity = cosine_like(source_tokens, target_tokens)
            if best is None or similarity > best[1]:
                best = (target, similarity)
        return best

    def _transformation_hint(self, source: Element, target: Element) -> str:
        source_text = f"{source.path} {source.scope_note or ''}".lower()
        target_text = f"{target.path} {target.scope_note or ''}".lower()
        if "date" in source_text and "date" in target_text:
            return "normalize date format to ISO-8601"
        if "name" in source_text and "title" in target_text:
            return "may require normalization and title-casing"
        if "identifier" in source_text and "identifier" in target_text:
            return "preserve identifier namespace and avoid lossy truncation"
        return "direct mapping; validate cardinality and datatype"

    def _semantic_loss(self, source: Element, target: Element) -> bool:
        source_card = {
            c.value for c in source.constraints if c.kind.value == "cardinality"
        }
        target_card = {
            c.value for c in target.constraints if c.kind.value == "cardinality"
        }
        if source_card and target_card and source_card != target_card:
            return True
        return False
