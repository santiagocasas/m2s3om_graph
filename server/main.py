import json
import os
import re
from pathlib import Path
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from m2s3om_graph.rdamsc.llm_runtime import (
    llm_chat_completions_url,
    load_llm_runtime_config,
)

app = FastAPI(title="M2S3OM-graph Suggestion API")

# Serve built Vite frontend - mount after routes to avoid shadowing API
static_dir = Path(__file__).parent.parent / "web" / "dist"
public_dir = Path(__file__).parent.parent / "web" / "public"

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "SUGGEST_API_ALLOWED_ORIGINS", "http://localhost:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)

class SuggestRequest(BaseModel):
    source_standard: str
    target_standard: str
    source_field: str
    target_schema_fields: list[str]
    context: Optional[str] = None


class CandidateRule(BaseModel):
    source_path: str
    target_path: Optional[str] = None
    mapping_type: str
    confidence: float
    evidence: str
    notes: Optional[str] = None


class ConvertRequest(BaseModel):
    source_xml: str
    source_format: str
    target_format: str
    source_profile: Optional[str] = None


class ConvertResponse(BaseModel):
    target_xml: str
    source_ir: dict
    target_ir: dict
    applied_rule_ids: list[str]
    unmapped_fields: list[str]
    semantic_loss_rules: list[str]
    ambiguous_rules: list[str]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/suggest", response_model=list[CandidateRule])
def suggest(req: SuggestRequest):
    config = load_llm_runtime_config()
    if not config.api_key:
        raise HTTPException(500, "BLABLADOR_API_KEY not configured on this Space")

    prompt = build_prompt(req)
    raw = _suggest_with_request_guard(prompt)
    return parse_candidates(raw)


@app.post("/convert", response_model=ConvertResponse)
def convert(req: ConvertRequest):
    from pathlib import Path
    from m2s3om_graph.transform.parsers import (
        parse_oai_dc_xml_to_ir,
        parse_datacite_xml_to_ir,
        parse_marcxml_to_ir,
    )
    from m2s3om_graph.transform.serializers import ir_to_datacite_xml, ir_to_dublin_core_xml
    from m2s3om_graph.transform.apply import apply_mapping_rules
    from m2s3om_graph.db.models import MappingRuleRecord, MappingType

    parser_map = {
        "oai_dc_xml": parse_oai_dc_xml_to_ir,
        "datacite_xml": parse_datacite_xml_to_ir,
        "marcxml": parse_marcxml_to_ir,
    }
    serializer_map = {
        "oai_dc_xml": ir_to_dublin_core_xml,
        "datacite_xml": ir_to_datacite_xml,
    }

    parser = parser_map.get(req.source_format)
    if parser is None:
        raise HTTPException(400, f"Unsupported source format: {req.source_format}")

    serializer = serializer_map.get(req.target_format)
    if serializer is None:
        raise HTTPException(
            400,
            f"Target format '{req.target_format}' cannot be produced: no serializer "
            f"is implemented for it yet. Supported targets: {sorted(serializer_map)}.",
        )

    try:
        source_ir = parser(req.source_xml)
    except Exception as exc:
        raise HTTPException(400, f"Failed to parse source XML: {exc}")

    # Format -> standard name mapping for crosswalk lookup
    format_to_standard = {
        "oai_dc_xml": "dcterms",
        "datacite_xml": "datacite44",
        "marcxml": "marc",
    }
    source_std = format_to_standard.get(req.source_format)
    target_std = format_to_standard.get(req.target_format)
    if not source_std or not target_std:
        raise HTTPException(400, "Format to standard mapping not defined")

    # Load crosswalk graph
    graph_path = Path(__file__).parent.parent / "web" / "public" / "data" / "crosswalk_graph.json"
    if not graph_path.exists():
        raise HTTPException(500, "crosswalk_graph.json not found")
    import json
    graph = json.loads(graph_path.read_text())
    crosswalk = None
    for cw in graph.get("crosswalks", []):
        if cw.get("source") == source_std and cw.get("target") == target_std:
            crosswalk = cw
            break
    if crosswalk is None:
        # Try reverse direction
        for cw in graph.get("crosswalks", []):
            if cw.get("source") == target_std and cw.get("target") == source_std:
                crosswalk = cw
                break
    if crosswalk is None:
        raise HTTPException(
            404,
            f"No crosswalk found between '{source_std}' and '{target_std}'. "
            f"Conversion between {req.source_format} and {req.target_format} is not "
            "supported yet.",
        )

    # Build MappingRuleRecord list from JSON
    rules = []
    for r in crosswalk.get("rules", []):
        try:
            mt = MappingType(r.get("mapping_type", "DIRECT").lower())
        except Exception:
            mt = MappingType.DIRECT
        rule = MappingRuleRecord(
            id=r.get("record_id", ""),
            crosswalk_id=crosswalk.get("id", ""),
            source_paths=r.get("source_paths", []),
            target_paths=r.get("target_paths", []),
            mapping_type=mt,
            confidence=float(r.get("confidence", 1.0)),
            semantic_loss=bool(r.get("semantic_loss", False)),
            ambiguity=bool(r.get("ambiguity", False)),
            transform=r.get("transform", {}),
            notes=r.get("notes"),
        )
        rules.append(rule)

    # Apply rules
    # If reverse direction, swap source/target? For simplicity assume forward.
    target_ir, report = apply_mapping_rules(source_ir, rules)

    try:
        target_xml = serializer(target_ir)
    except Exception as exc:
        raise HTTPException(500, f"Failed to serialize target XML: {exc}")

    def ir_to_dict(ir):
        out = {}
        for k, values in ir.items():
            out[k] = [v.model_dump() if hasattr(v, "model_dump") else v for v in values]
        return out

    return ConvertResponse(
        target_xml=target_xml,
        source_ir=ir_to_dict(source_ir),
        target_ir=ir_to_dict(target_ir),
        applied_rule_ids=report.applied_rule_ids,
        unmapped_fields=report.unmapped_fields,
        semantic_loss_rules=report.semantic_loss_rules,
        ambiguous_rules=report.ambiguous_rules,
    )


def build_prompt(req: SuggestRequest) -> str:
    context_line = f"\nAdditional context: {req.context}" if req.context else ""
    return f"""You are a metadata standards expert.

Suggest a mapping rule for this uncovered field.

Source standard: {req.source_standard}
Target standard: {req.target_standard}
Source field: {req.source_field}
Candidate target fields in {req.target_standard}: {', '.join(req.target_schema_fields)}{context_line}

Return a JSON array of 1 to 3 candidate rules, each with this exact shape:
{{
  "source_path": "...",
  "target_path": "... or null if no good match exists",
  "mapping_type": "direct|missing|conditional|aggregation",
  "confidence": 0.0,
  "evidence": "why this mapping makes sense, grounded in the field names and standard descriptions given above, do not invent facts not present here",
  "notes": "free text"
}}

Return ONLY the JSON array. No preamble, no markdown code fences.
"""


def call_blablador(prompt: str) -> str:
    config = load_llm_runtime_config()
    response = requests.post(
        llm_chat_completions_url(config),
        headers={"Authorization": f"Bearer {config.api_key}"},
        json={
            "model": config.model,
            "temperature": 0,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You suggest candidate metadata mapping rules as strict JSON. "
                        "Return CandidateRule objects with source_path, target_path, "
                        "mapping_type, confidence, evidence, and optional notes."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        },
        timeout=config.timeout_s,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def _suggest_with_request_guard(prompt: str) -> str:
    try:
        return call_blablador(prompt)
    except requests.RequestException as exc:
        raise HTTPException(502, f"Blablador request failed: {exc}") from exc


def parse_candidates(raw: str) -> list[dict]:
    # Strip markdown code fences if the model added them despite instructions.
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise HTTPException(502, f"Could not parse model output as JSON: {e}")

# Serve static frontend after API routes
if public_dir.exists():
    app.mount("/data", StaticFiles(directory=str(public_dir / "data")), name="data")
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
