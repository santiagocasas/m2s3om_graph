import hashlib
import os
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, cast

from surrealdb import Surreal

from .models import (
    ArtifactChunkRecord,
    ArtifactDocumentRecord,
    CrosswalkBundle,
    CrosswalkRecord,
    ElementRecord,
    EvidenceRecord,
    MappingRuleRecord,
    StandardRecord,
)
from .surreal_schema import crosswalk_surreal_schema


class CrosswalkStore:
    def apply_schema(self) -> None:
        raise NotImplementedError

    def upsert_standard(self, standard: StandardRecord) -> StandardRecord:
        raise NotImplementedError

    def upsert_element(self, element: ElementRecord) -> ElementRecord:
        raise NotImplementedError

    def upsert_crosswalk(self, crosswalk: CrosswalkRecord) -> CrosswalkRecord:
        raise NotImplementedError

    def upsert_mapping_rule(self, rule: MappingRuleRecord) -> MappingRuleRecord:
        raise NotImplementedError

    def upsert_evidence(self, evidence: EvidenceRecord) -> EvidenceRecord:
        raise NotImplementedError

    def upsert_artifact_document(
        self, document: ArtifactDocumentRecord
    ) -> ArtifactDocumentRecord:
        raise NotImplementedError

    def upsert_artifact_chunk(self, chunk: ArtifactChunkRecord) -> ArtifactChunkRecord:
        raise NotImplementedError

    def list_crosswalks(self) -> list[CrosswalkRecord]:
        raise NotImplementedError

    def list_standards(self) -> list[StandardRecord]:
        raise NotImplementedError

    def list_elements(self, standard_id: str) -> list[ElementRecord]:
        raise NotImplementedError

    def list_artifact_documents(
        self, crosswalk_id: str
    ) -> list[ArtifactDocumentRecord]:
        raise NotImplementedError

    def list_artifact_chunks(self, crosswalk_id: str) -> list[ArtifactChunkRecord]:
        raise NotImplementedError

    def get_crosswalk_bundle(self, crosswalk_id: str) -> CrosswalkBundle | None:
        raise NotImplementedError


def stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.md5(
        "|".join(parts).encode("utf-8"), usedforsecurity=False
    ).hexdigest()[:16]
    return f"{prefix}:{digest}"


@dataclass
class InMemoryCrosswalkStore(CrosswalkStore):
    standards: dict[str, StandardRecord] = field(default_factory=dict)
    elements: dict[str, ElementRecord] = field(default_factory=dict)
    crosswalks: dict[str, CrosswalkRecord] = field(default_factory=dict)
    rules: dict[str, MappingRuleRecord] = field(default_factory=dict)
    evidences: dict[str, EvidenceRecord] = field(default_factory=dict)
    artifact_documents: dict[str, ArtifactDocumentRecord] = field(default_factory=dict)
    artifact_chunks: dict[str, ArtifactChunkRecord] = field(default_factory=dict)
    by_standard: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    rules_by_crosswalk: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    evidence_by_rule: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    docs_by_crosswalk: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )
    chunks_by_crosswalk: dict[str, list[str]] = field(
        default_factory=lambda: defaultdict(list)
    )

    def apply_schema(self) -> None:
        rebuilt_by_standard: dict[str, list[str]] = defaultdict(list)
        for element in self.elements.values():
            rebuilt_by_standard[element.standard_id].append(element.id)
        self.by_standard = rebuilt_by_standard

        rebuilt_rules_by_crosswalk: dict[str, list[str]] = defaultdict(list)
        for rule in self.rules.values():
            rebuilt_rules_by_crosswalk[rule.crosswalk_id].append(rule.id)
        self.rules_by_crosswalk = rebuilt_rules_by_crosswalk

        rebuilt_evidence_by_rule: dict[str, list[str]] = defaultdict(list)
        for evidence in self.evidences.values():
            rebuilt_evidence_by_rule[evidence.mapping_rule_id].append(evidence.id)
        self.evidence_by_rule = rebuilt_evidence_by_rule

        rebuilt_docs_by_crosswalk: dict[str, list[str]] = defaultdict(list)
        for document in self.artifact_documents.values():
            rebuilt_docs_by_crosswalk[document.crosswalk_id].append(document.id)
        self.docs_by_crosswalk = rebuilt_docs_by_crosswalk

        rebuilt_chunks_by_crosswalk: dict[str, list[str]] = defaultdict(list)
        for chunk in self.artifact_chunks.values():
            rebuilt_chunks_by_crosswalk[chunk.crosswalk_id].append(chunk.id)
        self.chunks_by_crosswalk = rebuilt_chunks_by_crosswalk

    def upsert_standard(self, standard: StandardRecord) -> StandardRecord:
        self.standards[standard.id] = standard
        return standard

    def upsert_element(self, element: ElementRecord) -> ElementRecord:
        self.elements[element.id] = element
        if element.id not in self.by_standard[element.standard_id]:
            self.by_standard[element.standard_id].append(element.id)
        return element

    def upsert_crosswalk(self, crosswalk: CrosswalkRecord) -> CrosswalkRecord:
        self.crosswalks[crosswalk.id] = crosswalk
        return crosswalk

    def upsert_mapping_rule(self, rule: MappingRuleRecord) -> MappingRuleRecord:
        self.rules[rule.id] = rule
        if rule.id not in self.rules_by_crosswalk[rule.crosswalk_id]:
            self.rules_by_crosswalk[rule.crosswalk_id].append(rule.id)
        return rule

    def upsert_evidence(self, evidence: EvidenceRecord) -> EvidenceRecord:
        self.evidences[evidence.id] = evidence
        if evidence.id not in self.evidence_by_rule[evidence.mapping_rule_id]:
            self.evidence_by_rule[evidence.mapping_rule_id].append(evidence.id)
        return evidence

    def upsert_artifact_document(
        self, document: ArtifactDocumentRecord
    ) -> ArtifactDocumentRecord:
        self.artifact_documents[document.id] = document
        if document.id not in self.docs_by_crosswalk[document.crosswalk_id]:
            self.docs_by_crosswalk[document.crosswalk_id].append(document.id)
        return document

    def upsert_artifact_chunk(self, chunk: ArtifactChunkRecord) -> ArtifactChunkRecord:
        self.artifact_chunks[chunk.id] = chunk
        if chunk.id not in self.chunks_by_crosswalk[chunk.crosswalk_id]:
            self.chunks_by_crosswalk[chunk.crosswalk_id].append(chunk.id)
        return chunk

    def list_crosswalks(self) -> list[CrosswalkRecord]:
        return sorted(self.crosswalks.values(), key=lambda x: x.created_at)

    def list_standards(self) -> list[StandardRecord]:
        return sorted(self.standards.values(), key=lambda x: x.name.lower())

    def list_elements(self, standard_id: str) -> list[ElementRecord]:
        ids = self.by_standard.get(standard_id, [])
        return [self.elements[x] for x in ids if x in self.elements]

    def list_artifact_documents(
        self, crosswalk_id: str
    ) -> list[ArtifactDocumentRecord]:
        ids = self.docs_by_crosswalk.get(crosswalk_id, [])
        return [self.artifact_documents[x] for x in ids if x in self.artifact_documents]

    def list_artifact_chunks(self, crosswalk_id: str) -> list[ArtifactChunkRecord]:
        ids = self.chunks_by_crosswalk.get(crosswalk_id, [])
        rows = [self.artifact_chunks[x] for x in ids if x in self.artifact_chunks]
        return sorted(rows, key=lambda x: (x.document_id, x.ordinal))

    def get_crosswalk_bundle(self, crosswalk_id: str) -> CrosswalkBundle | None:
        crosswalk = self.crosswalks.get(crosswalk_id)
        if crosswalk is None:
            return None
        source = self.standards.get(crosswalk.source_standard_id)
        target = self.standards.get(crosswalk.target_standard_id)
        if source is None or target is None:
            return None
        rules: list[MappingRuleRecord] = []
        for rule_id in self.rules_by_crosswalk.get(crosswalk_id, []):
            rule = self.rules[rule_id]
            evidence = [
                self.evidences[eid]
                for eid in self.evidence_by_rule.get(rule.id, [])
                if eid in self.evidences
            ]
            rules.append(rule.model_copy(update={"evidence": evidence}))
        return CrosswalkBundle(
            crosswalk=crosswalk,
            source_standard=source,
            target_standard=target,
            rules=rules,
        )


class SurrealCrosswalkStore(CrosswalkStore):
    def __init__(
        self,
        url: str,
        username: str,
        password: str,
        namespace: str,
        database: str,
    ):
        self._surreal = Surreal(url)
        if url != "mem://":
            _ = self._surreal.signin({"username": username, "password": password})
        self._surreal.use(namespace, database)

    def _query(self, statement: str, vars: dict[str, object] | None = None) -> object:
        query_vars = cast(Any, vars) if vars is not None else None
        result = self._surreal.query(statement, query_vars)
        if isinstance(result, str):
            raise RuntimeError(result)
        return result

    def _relate(self, statement: str, vars: dict[str, object]) -> None:
        try:
            _ = self._query(statement, vars)
        except RuntimeError as exc:
            text = str(exc).lower()
            if "already exists" in text:
                return
            raise

    @staticmethod
    def _normalize_id(value: object) -> str:
        raw = str(getattr(value, "id", value))
        if ":" not in raw:
            return raw
        return raw.split(":", 1)[1]

    def _normalize_row(self, row: dict[str, object]) -> dict[str, object]:
        out: dict[str, object] = dict(row)
        if "id" in out:
            out["id"] = self._normalize_id(out["id"])
        return out

    def apply_schema(self) -> None:
        _ = self._query(crosswalk_surreal_schema())

    def upsert_standard(self, standard: StandardRecord) -> StandardRecord:
        _ = self._query(
            "UPSERT ONLY type::thing('standard', $id) CONTENT $obj",
            {"id": standard.id, "obj": standard.model_dump(mode="json")},
        )
        return standard

    def upsert_element(self, element: ElementRecord) -> ElementRecord:
        _ = self._query(
            "UPSERT ONLY type::thing('element', $id) CONTENT $obj",
            {"id": element.id, "obj": element.model_dump(mode="json")},
        )
        if element.parent_element_id:
            self._relate(
                "RELATE (type::thing('element',$parent))->element_parent_of->(type::thing('element',$child))",
                {"parent": element.parent_element_id, "child": element.id},
            )
        self._relate(
            "RELATE (type::thing('standard',$sid))->standard_has_element->(type::thing('element',$eid))",
            {"sid": element.standard_id, "eid": element.id},
        )
        return element

    def upsert_crosswalk(self, crosswalk: CrosswalkRecord) -> CrosswalkRecord:
        payload = crosswalk.model_dump(mode="json")
        _ = self._query(
            "UPSERT ONLY type::thing('crosswalk', $id) CONTENT $obj",
            {"id": crosswalk.id, "obj": payload},
        )
        self._relate(
            "RELATE (type::thing('crosswalk',$cw))->crosswalk_maps_from->(type::thing('standard',$src))",
            {"cw": crosswalk.id, "src": crosswalk.source_standard_id},
        )
        self._relate(
            "RELATE (type::thing('crosswalk',$cw))->crosswalk_maps_to->(type::thing('standard',$dst))",
            {"cw": crosswalk.id, "dst": crosswalk.target_standard_id},
        )
        return crosswalk

    def upsert_mapping_rule(self, rule: MappingRuleRecord) -> MappingRuleRecord:
        payload = rule.model_dump(mode="json")
        payload.pop("evidence", None)
        _ = self._query(
            "UPSERT ONLY type::thing('mapping_rule', $id) CONTENT $obj",
            {"id": rule.id, "obj": payload},
        )
        self._relate(
            "RELATE (type::thing('crosswalk',$cw))->crosswalk_has_rule->(type::thing('mapping_rule',$rid))",
            {"cw": rule.crosswalk_id, "rid": rule.id},
        )
        return rule

    def upsert_evidence(self, evidence: EvidenceRecord) -> EvidenceRecord:
        _ = self._query(
            "UPSERT ONLY type::thing('evidence', $id) CONTENT $obj",
            {"id": evidence.id, "obj": evidence.model_dump(mode="json")},
        )
        self._relate(
            "RELATE (type::thing('mapping_rule',$rid))->rule_has_evidence->(type::thing('evidence',$eid))",
            {"rid": evidence.mapping_rule_id, "eid": evidence.id},
        )
        return evidence

    def upsert_artifact_document(
        self, document: ArtifactDocumentRecord
    ) -> ArtifactDocumentRecord:
        _ = self._query(
            "UPSERT ONLY type::thing('artifact_document', $id) CONTENT $obj",
            {"id": document.id, "obj": document.model_dump(mode="json")},
        )
        self._relate(
            "RELATE (type::thing('crosswalk',$cw))->crosswalk_has_artifact->(type::thing('artifact_document',$doc))",
            {"cw": document.crosswalk_id, "doc": document.id},
        )
        return document

    def upsert_artifact_chunk(self, chunk: ArtifactChunkRecord) -> ArtifactChunkRecord:
        _ = self._query(
            "UPSERT ONLY type::thing('artifact_chunk', $id) CONTENT $obj",
            {"id": chunk.id, "obj": chunk.model_dump(mode="json")},
        )
        self._relate(
            "RELATE (type::thing('artifact_document',$doc))->artifact_has_chunk->(type::thing('artifact_chunk',$chunk))",
            {"doc": chunk.document_id, "chunk": chunk.id},
        )
        return chunk

    def list_crosswalks(self) -> list[CrosswalkRecord]:
        rows = self._query("SELECT * FROM crosswalk ORDER BY created_at DESC")
        if not isinstance(rows, list):
            return []
        return [
            CrosswalkRecord.model_validate(self._normalize_row(row))
            for row in rows
            if isinstance(row, dict)
        ]

    def list_standards(self) -> list[StandardRecord]:
        rows = self._query("SELECT * FROM standard ORDER BY name")
        if not isinstance(rows, list):
            return []
        return [
            StandardRecord.model_validate(self._normalize_row(row))
            for row in rows
            if isinstance(row, dict)
        ]

    def list_elements(self, standard_id: str) -> list[ElementRecord]:
        rows = self._query(
            "SELECT * FROM element WHERE standard_id = $sid",
            {"sid": standard_id},
        )
        if not isinstance(rows, list):
            return []
        return [
            ElementRecord.model_validate(self._normalize_row(row))
            for row in rows
            if isinstance(row, dict)
        ]

    def list_artifact_documents(
        self, crosswalk_id: str
    ) -> list[ArtifactDocumentRecord]:
        rows = self._query(
            "SELECT * FROM artifact_document WHERE crosswalk_id = $id ORDER BY fetched_at DESC",
            {"id": crosswalk_id},
        )
        if not isinstance(rows, list):
            return []
        return [
            ArtifactDocumentRecord.model_validate(self._normalize_row(row))
            for row in rows
            if isinstance(row, dict)
        ]

    def list_artifact_chunks(self, crosswalk_id: str) -> list[ArtifactChunkRecord]:
        rows = self._query(
            "SELECT * FROM artifact_chunk WHERE crosswalk_id = $id ORDER BY document_id, ordinal",
            {"id": crosswalk_id},
        )
        if not isinstance(rows, list):
            return []
        return [
            ArtifactChunkRecord.model_validate(self._normalize_row(row))
            for row in rows
            if isinstance(row, dict)
        ]

    def get_crosswalk_bundle(self, crosswalk_id: str) -> CrosswalkBundle | None:
        cw = self._query(
            "SELECT * FROM ONLY type::thing('crosswalk',$id)",
            {"id": crosswalk_id},
        )
        if not isinstance(cw, dict):
            return None
        crosswalk = CrosswalkRecord.model_validate(self._normalize_row(cw))
        source = self._query(
            "SELECT * FROM ONLY type::thing('standard',$id)",
            {"id": crosswalk.source_standard_id},
        )
        target = self._query(
            "SELECT * FROM ONLY type::thing('standard',$id)",
            {"id": crosswalk.target_standard_id},
        )
        rules_rows = self._query(
            "SELECT * FROM mapping_rule WHERE crosswalk_id = $id",
            {"id": crosswalk_id},
        )
        rules: list[MappingRuleRecord] = []
        for rule_row in rules_rows if isinstance(rules_rows, list) else []:
            if not isinstance(rule_row, dict):
                continue
            rid = rule_row.get("id")
            rid_value = str(getattr(rid, "id", rid))
            ev_rows = self._query(
                "SELECT * FROM evidence WHERE mapping_rule_id = $id",
                {"id": rid_value},
            )
            evidence = [
                EvidenceRecord.model_validate(self._normalize_row(x))
                for x in (ev_rows if isinstance(ev_rows, list) else [])
                if isinstance(x, dict)
            ]
            base = MappingRuleRecord.model_validate(self._normalize_row(rule_row))
            rules.append(base.model_copy(update={"evidence": evidence}))
        if not isinstance(source, dict) or not isinstance(target, dict):
            return None
        return CrosswalkBundle(
            crosswalk=crosswalk,
            source_standard=StandardRecord.model_validate(self._normalize_row(source)),
            target_standard=StandardRecord.model_validate(self._normalize_row(target)),
            rules=rules,
        )


def build_default_store() -> CrosswalkStore:
    use_surreal = os.getenv("M2S3OM_USE_SURREAL", "").strip().lower()
    if use_surreal in {"1", "true", "yes", "on"}:
        return SurrealCrosswalkStore(
            url=os.getenv("M2S3OM_DB_URL", "ws://localhost:8000/rpc"),
            username=_required_non_root_secret("M2S3OM_DB_USER"),
            password=_required_non_root_secret("M2S3OM_DB_PASSWORD"),
            namespace=os.getenv("M2S3OM_DB_NS", "m2s3om_graph"),
            database=os.getenv("M2S3OM_DB_NAME", "crosswalk"),
        )
    return InMemoryCrosswalkStore()


def _required_non_root_secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be set when M2S3OM_USE_SURREAL is enabled")
    if value.lower() == "root":
        raise RuntimeError(
            f"{name} cannot use insecure default 'root' when M2S3OM_USE_SURREAL is enabled"
        )
    return value
