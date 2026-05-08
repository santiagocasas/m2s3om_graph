from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MappingStatus(str, Enum):
    PROPOSED = "proposed"
    REVIEWED = "reviewed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class Citation(BaseModel):
    chunk_id: str
    url: str | None = None
    anchor: str | None = None
    snippet: str


class MappingRecord(BaseModel):
    id: str
    crosswalk_id: str
    source_element_id: str
    target_element_id: str
    confidence: float = Field(ge=0.0, le=1.0)
    justification: str
    transformation_hint: str
    ambiguity_flag: bool = False
    semantic_loss_flag: bool = False
    citations: list[Citation] = Field(default_factory=list)
    status: MappingStatus = MappingStatus.PROPOSED


class Crosswalk(BaseModel):
    id: str
    source_standard_id: str
    target_standard_id: str
    created_at: str = Field(default_factory=utc_now_iso)
    agent_version: str = "m2s3om_graph-mapper-v1"
