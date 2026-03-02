from pydantic import BaseModel, Field


class IRValue(BaseModel):
    text: str
    lang: str | None = None
    scheme: str | None = None
    uri: str | None = None
    attrs: dict[str, str] = Field(default_factory=dict)
    source_record_id: str | None = None
    source_path: str | None = None
    source_format: str | None = None


type IRRecord = dict[str, list[IRValue]]


def add_ir_value(ir: IRRecord, key: str, value: IRValue) -> None:
    if key not in ir:
        ir[key] = []
    ir[key].append(value)


def get_first_text(ir: IRRecord, key: str) -> str | None:
    values = ir.get(key)
    if not values:
        return None
    return values[0].text
