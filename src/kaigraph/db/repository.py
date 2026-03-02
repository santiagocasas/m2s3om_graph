from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field

from kaigraph.models import Chunk, Crosswalk, Element, MappingRecord, Standard


class CrosswalkRepository:
    def upsert_standard(self, standard: Standard) -> None:
        raise NotImplementedError

    def upsert_elements(self, elements: Iterable[Element]) -> None:
        raise NotImplementedError

    def upsert_chunks(self, chunks: Iterable[Chunk]) -> None:
        raise NotImplementedError

    def save_crosswalk(
        self, crosswalk: Crosswalk, mappings: Iterable[MappingRecord]
    ) -> None:
        raise NotImplementedError

    def list_standards(self) -> list[Standard]:
        raise NotImplementedError

    def list_elements(self, standard_id: str) -> list[Element]:
        raise NotImplementedError

    def list_mappings(self, crosswalk_id: str | None = None) -> list[MappingRecord]:
        raise NotImplementedError

    def all_chunks(self) -> list[Chunk]:
        raise NotImplementedError


@dataclass
class InMemoryCrosswalkRepository(CrosswalkRepository):
    standards: dict[str, Standard] = field(default_factory=dict)
    elements: dict[str, Element] = field(default_factory=dict)
    chunks: dict[str, Chunk] = field(default_factory=dict)
    crosswalks: dict[str, Crosswalk] = field(default_factory=dict)
    mappings: dict[str, MappingRecord] = field(default_factory=dict)
    by_standard: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))

    def upsert_standard(self, standard: Standard) -> None:
        self.standards[standard.id] = standard

    def upsert_elements(self, elements: Iterable[Element]) -> None:
        for element in elements:
            self.elements[element.id] = element
            if element.id not in self.by_standard[element.standard_id]:
                self.by_standard[element.standard_id].append(element.id)

    def upsert_chunks(self, chunks: Iterable[Chunk]) -> None:
        for chunk in chunks:
            self.chunks[chunk.id] = chunk

    def save_crosswalk(
        self, crosswalk: Crosswalk, mappings: Iterable[MappingRecord]
    ) -> None:
        self.crosswalks[crosswalk.id] = crosswalk
        for mapping in mappings:
            self.mappings[mapping.id] = mapping

    def list_standards(self) -> list[Standard]:
        return sorted(self.standards.values(), key=lambda x: x.name.lower())

    def list_elements(self, standard_id: str) -> list[Element]:
        ids = self.by_standard.get(standard_id, [])
        return [self.elements[id_] for id_ in ids if id_ in self.elements]

    def list_mappings(self, crosswalk_id: str | None = None) -> list[MappingRecord]:
        values = list(self.mappings.values())
        if crosswalk_id is None:
            return values
        return [x for x in values if x.crosswalk_id == crosswalk_id]

    def all_chunks(self) -> list[Chunk]:
        return list(self.chunks.values())
