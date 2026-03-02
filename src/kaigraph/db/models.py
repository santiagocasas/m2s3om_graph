from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MappingType(str, Enum):
    DIRECT = "direct"
    MISSING = "missing"
    CONDITIONAL = "conditional"
    AGGREGATION = "aggregation"
    DECOMPOSITION = "decomposition"
    PASSTHROUGH = "passthrough"


class StandardRecord(BaseModel):
    id: str
    name: str
    namespace: str | None = None
    version: str | None = None
    urls: dict[str, str] = Field(default_factory=dict)
    external_ids: dict[str, str] = Field(default_factory=dict)


class ElementRecord(BaseModel):
    id: str
    standard_id: str
    path: str
    label: str
    full_iri: str | None = None
    notes: str | None = None
    parent_element_id: str | None = None


class CrosswalkRecord(BaseModel):
    id: str
    name: str
    source_standard_id: str
    target_standard_id: str
    version: str | None = None
    doi: str | None = None
    msc_id: str | None = None
    doc_uri: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class EvidenceRecord(BaseModel):
    id: str
    mapping_rule_id: str
    source: str = "PDF"
    doc_uri: str
    page_number: int
    row_id: str
    snippet: str
    bbox: dict[str, float] | None = None
    chunk_id: str | None = None


class ArtifactDocumentRecord(BaseModel):
    id: str
    crosswalk_id: str
    source_url: str
    resolved_url: str
    content_type: str
    extension: str
    markdown: str
    status: str = "fetched"
    fetched_at: datetime = Field(default_factory=utc_now)


class ArtifactChunkRecord(BaseModel):
    id: str
    document_id: str
    crosswalk_id: str
    ordinal: int
    text: str


class MappingRuleRecord(BaseModel):
    id: str
    crosswalk_id: str
    source_element_id: str | None = None
    source_paths: list[str] = Field(default_factory=list)
    target_element_id: str | None = None
    target_paths: list[str] = Field(default_factory=list)
    mapping_type: MappingType
    confidence: float = Field(ge=0.0, le=1.0)
    semantic_loss: bool = False
    ambiguity: bool = False
    transform: dict[str, object] = Field(default_factory=dict)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    notes: str | None = None


class CrosswalkBundle(BaseModel):
    crosswalk: CrosswalkRecord
    source_standard: StandardRecord
    target_standard: StandardRecord
    rules: list[MappingRuleRecord]


class IRStoredRecord(BaseModel):
    id: str
    source_record_id: str
    source_format: str
    payload: dict[str, list[dict[str, object]]]
    created_at: datetime = Field(default_factory=utc_now)


class ComparisonResultRecord(BaseModel):
    id: str
    benchmark_run_id: str
    source_record_id: str
    crosswalk_id: str
    direction: str
    metrics: dict[str, float]
    missing_fields: list[str] = Field(default_factory=list)
    mismatched_fields: list[str] = Field(default_factory=list)
    semantic_loss_rate: float = 0.0
    diff_payload: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class BenchmarkRunRecord(BaseModel):
    id: str
    crosswalk_id: str
    endpoint: str
    direction: str
    n_records: int
    summary_metrics: dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
