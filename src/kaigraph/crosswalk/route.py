from collections import deque
from dataclasses import dataclass
from pathlib import Path

from kaigraph.db import (
    CrosswalkBundle,
    CrosswalkStore,
    MappingRuleRecord,
    StandardRecord,
)
from kaigraph.sssom import load_sssom_rules

from .reverse import derive_reverse_rules

FORMAT_STANDARD_HINTS: dict[str, tuple[str, ...]] = {
    "oai_dc_xml": ("dublin core", "dcmi", "dcterms"),
    "datacite_xml": ("datacite",),
}


@dataclass(frozen=True)
class ConversionStep:
    crosswalk_id: str
    crosswalk_name: str
    source_standard_id: str
    target_standard_id: str
    direction: str
    rules: list[MappingRuleRecord]


def _text_matches(value: str, hints: tuple[str, ...]) -> bool:
    lowered = value.lower()
    return any(hint in lowered for hint in hints)


def _candidate_standard_ids(store: CrosswalkStore, payload_format: str) -> list[str]:
    hints = FORMAT_STANDARD_HINTS.get(payload_format)
    if not hints:
        return []

    matches: list[str] = []
    for standard in store.list_standards():
        haystacks = [standard.id, standard.name, standard.namespace or ""]
        if any(_text_matches(part, hints) for part in haystacks):
            matches.append(standard.id)
    return matches


def matched_standards_for_format(
    store: CrosswalkStore, payload_format: str
) -> list[StandardRecord]:
    matched_ids = set(_candidate_standard_ids(store, payload_format))
    return [
        standard for standard in store.list_standards() if standard.id in matched_ids
    ]


def _authoritative_rules(
    bundle: CrosswalkBundle, sssom_dir: Path
) -> list[MappingRuleRecord]:
    path = sssom_dir / f"{bundle.crosswalk.id}.sssom.tsv"
    if path.exists():
        rules = load_sssom_rules(path, bundle.crosswalk.id)
        if rules:
            return rules
    return bundle.rules


def _graph_steps(
    store: CrosswalkStore,
    sssom_dir: Path,
) -> dict[str, list[tuple[str, ConversionStep]]]:
    graph: dict[str, list[tuple[str, ConversionStep]]] = {}

    for crosswalk in store.list_crosswalks():
        bundle = store.get_crosswalk_bundle(crosswalk.id)
        if bundle is None:
            continue
        rules = _authoritative_rules(bundle, sssom_dir)
        if not rules:
            continue

        forward = ConversionStep(
            crosswalk_id=crosswalk.id,
            crosswalk_name=crosswalk.name,
            source_standard_id=crosswalk.source_standard_id,
            target_standard_id=crosswalk.target_standard_id,
            direction="forward",
            rules=rules,
        )
        graph.setdefault(crosswalk.source_standard_id, []).append(
            (crosswalk.target_standard_id, forward)
        )

        reverse_rules = derive_reverse_rules(bundle.model_copy(update={"rules": rules}))
        if reverse_rules:
            reverse = ConversionStep(
                crosswalk_id=crosswalk.id,
                crosswalk_name=crosswalk.name,
                source_standard_id=crosswalk.target_standard_id,
                target_standard_id=crosswalk.source_standard_id,
                direction="reverse",
                rules=reverse_rules,
            )
            graph.setdefault(crosswalk.target_standard_id, []).append(
                (crosswalk.source_standard_id, reverse)
            )

    return graph


def resolve_conversion_route(
    store: CrosswalkStore,
    source_format: str,
    target_format: str,
    sssom_dir: Path,
) -> list[ConversionStep]:
    if source_format == target_format:
        return []

    source_ids = _candidate_standard_ids(store, source_format)
    target_ids = set(_candidate_standard_ids(store, target_format))
    if not source_ids or not target_ids:
        return []

    graph = _graph_steps(store, sssom_dir)
    queue: deque[tuple[str, list[ConversionStep]]] = deque(
        (source_id, []) for source_id in source_ids
    )
    visited = set(source_ids)

    while queue:
        current, steps = queue.popleft()
        if current in target_ids:
            return steps
        for next_id, step in graph.get(current, []):
            if next_id in visited:
                continue
            visited.add(next_id)
            queue.append((next_id, [*steps, step]))

    return []


def available_target_formats(
    store: CrosswalkStore,
    source_format: str,
    sssom_dir: Path,
) -> list[str]:
    targets: list[str] = []
    for candidate in FORMAT_STANDARD_HINTS:
        if candidate == source_format:
            continue
        if resolve_conversion_route(store, source_format, candidate, sssom_dir):
            targets.append(candidate)
    return targets
