from enum import Enum

from pydantic import BaseModel, Field


class ConstraintType(str, Enum):
    CARDINALITY = "cardinality"
    DATATYPE = "datatype"
    VOCABULARY = "vocabulary"
    FORMAT = "format"


class Standard(BaseModel):
    id: str
    name: str
    version: str | None = None
    source_url: str | None = None
    description: str | None = None


class Constraint(BaseModel):
    kind: ConstraintType
    value: str


class Element(BaseModel):
    id: str
    standard_id: str
    path: str
    label: str
    scope_note: str | None = None
    constraints: list[Constraint] = Field(default_factory=list)


class Definition(BaseModel):
    id: str
    element_id: str
    text: str


class Example(BaseModel):
    id: str
    element_id: str
    text: str


class Chunk(BaseModel):
    id: str
    standard_id: str
    element_id: str | None = None
    content: str
    source_url: str | None = None
    anchor: str | None = None
    embedding: list[float] | None = None
