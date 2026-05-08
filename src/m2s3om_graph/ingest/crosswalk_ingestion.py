from pathlib import Path

from m2s3om_graph.db import (
    CrosswalkRecord,
    CrosswalkStore,
    ElementRecord,
    EvidenceRecord,
    MappingRuleRecord,
    MappingType,
    StandardRecord,
    stable_id,
)

from .pdf_crosswalk_parser import ParsedMappingRow, parse_mapping_pdf


DATACITE_STANDARD_ID = "datacite_4_4"
DC_STANDARD_ID = "dublin_core_terms"
CROSSWALK_ID = "datacite44_to_dcterms"

DATACITE_SPEC_URL = "https://schema.datacite.org/meta/kernel-4.4/"
DATACITE_DOCS_URL = "https://support.datacite.org/docs/datacite-metadata-schema-v44"
DCTERMS_SPEC_URL = "https://www.dublincore.org/specifications/dublin-core/dcmi-terms/"
DCTERMS_BASE_IRI = "http://purl.org/dc/terms/"


def _parent_row_id(row_id: str) -> str | None:
    if "." not in row_id:
        return None
    return row_id.rsplit(".", 1)[0]


def _dc_label(dc_term: str) -> str:
    if ":" in dc_term:
        return dc_term.split(":", 1)[1]
    return dc_term


def _mapping_confidence(mapping_type: MappingType) -> float:
    if mapping_type == MappingType.DIRECT:
        return 0.98
    if mapping_type == MappingType.CONDITIONAL:
        return 0.85
    if mapping_type == MappingType.AGGREGATION:
        return 0.78
    if mapping_type == MappingType.DECOMPOSITION:
        return 0.72
    if mapping_type == MappingType.MISSING:
        return 0.95
    return 0.65


def _dcterms_full_iri(path: str) -> str:
    if ":" not in path:
        return DCTERMS_BASE_IRI + path
    return DCTERMS_BASE_IRI + path.split(":", 1)[1]


def _build_transform(row: ParsedMappingRow) -> dict[str, object]:
    if row.mapping_type == MappingType.MISSING:
        return {"op": "drop", "reason": "Not present in Dublin Core"}
    if row.mapping_type == MappingType.CONDITIONAL:
        mapping = {case.key: case.value for case in row.cases}
        default_value = None
        for key, value in mapping.items():
            if key.lower().startswith("other relation types"):
                default_value = value
        op: dict[str, object] = {
            "op": "value_map",
            "field": row.datacite_property,
            "mapping": mapping,
        }
        if default_value:
            op["default"] = default_value
        return op
    if row.mapping_type == MappingType.AGGREGATION:
        return {
            "op": "concat",
            "sources": [row.row_id],
            "separator": "; ",
        }
    if row.mapping_type == MappingType.DECOMPOSITION:
        return {"op": "split", "source": row.row_id}
    return {"op": "copy"}


def ingest_datacite_to_dc_pdf(
    store: CrosswalkStore,
    pdf_path: str | Path,
    *,
    doc_uri: str | None = None,
) -> str:
    resolved = Path(pdf_path).resolve()
    if doc_uri is None:
        doc_uri = resolved.as_uri()

    store.apply_schema()

    datacite = StandardRecord(
        id=DATACITE_STANDARD_ID,
        name="DataCite",
        namespace="datacite",
        version="4.4",
        urls={
            "spec": DATACITE_SPEC_URL,
            "docs": DATACITE_DOCS_URL,
        },
    )
    dcterms = StandardRecord(
        id=DC_STANDARD_ID,
        name="Dublin Core Terms",
        namespace="dcterms",
        version="1.1",
        urls={
            "spec": DCTERMS_SPEC_URL,
        },
    )
    store.upsert_standard(datacite)
    store.upsert_standard(dcterms)

    crosswalk = CrosswalkRecord(
        id=CROSSWALK_ID,
        name="DataCite 4.4 to Dublin Core Terms",
        source_standard_id=datacite.id,
        target_standard_id=dcterms.id,
        version="4.4",
        doi="10.14454/qn00-qx85",
        doc_uri=doc_uri,
    )
    store.upsert_crosswalk(crosswalk)

    rows = parse_mapping_pdf(resolved, doc_uri=doc_uri)
    dc_cache: set[str] = set()

    for row in rows:
        source_element = ElementRecord(
            id=f"{datacite.id}:{row.row_id}",
            standard_id=datacite.id,
            path=row.row_id,
            label=row.datacite_property,
            notes=row.notes,
            parent_element_id=(
                f"{datacite.id}:{_parent_row_id(row.row_id)}"
                if _parent_row_id(row.row_id)
                else None
            ),
        )
        store.upsert_element(source_element)

        target_element_id: str | None = None
        target_paths: list[str] = []

        if row.dublin_core.startswith("dcterms:"):
            target_paths = [row.dublin_core]
            target_element_id = f"{dcterms.id}:{row.dublin_core}"
            if target_element_id not in dc_cache:
                dc_cache.add(target_element_id)
                store.upsert_element(
                    ElementRecord(
                        id=target_element_id,
                        standard_id=dcterms.id,
                        path=row.dublin_core,
                        label=_dc_label(row.dublin_core),
                        full_iri=_dcterms_full_iri(row.dublin_core),
                    )
                )

        if row.cases:
            for case in row.cases:
                target_paths.append(case.value)
                dc_id = f"{dcterms.id}:{case.value}"
                if dc_id not in dc_cache:
                    dc_cache.add(dc_id)
                    store.upsert_element(
                        ElementRecord(
                            id=dc_id,
                            standard_id=dcterms.id,
                            path=case.value,
                            label=_dc_label(case.value),
                            full_iri=_dcterms_full_iri(case.value),
                        )
                    )

        mapping_type = row.mapping_type
        if row.dublin_core == "Not present in Dublin Core":
            mapping_type = MappingType.MISSING

        rule = MappingRuleRecord(
            id=stable_id(
                "mapping_rule", crosswalk.id, row.row_id, row.datacite_property
            ),
            crosswalk_id=crosswalk.id,
            source_element_id=source_element.id,
            source_paths=[row.row_id, row.datacite_property],
            target_element_id=target_element_id,
            target_paths=sorted(set(target_paths)),
            mapping_type=mapping_type,
            confidence=_mapping_confidence(mapping_type),
            semantic_loss=mapping_type == MappingType.MISSING,
            ambiguity=mapping_type
            in {MappingType.CONDITIONAL, MappingType.AGGREGATION},
            transform=_build_transform(row),
            notes=row.notes,
        )
        store.upsert_mapping_rule(rule)

        evidence = EvidenceRecord(
            id=stable_id("evidence", rule.id, str(row.page_number), row.row_id),
            mapping_rule_id=rule.id,
            source="PDF",
            doc_uri=doc_uri,
            page_number=row.page_number,
            row_id=row.row_id,
            snippet=row.snippet,
        )
        store.upsert_evidence(evidence)

    return crosswalk.id
