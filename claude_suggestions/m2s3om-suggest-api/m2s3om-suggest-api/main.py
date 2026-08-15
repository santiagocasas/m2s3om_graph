import json
import re
from typing import Optional

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from m2s3om_graph.rdamsc.llm_runtime import (
    llm_chat_completions_url,
    load_llm_runtime_config,
)

app = FastAPI(title="M2S3OM-graph Suggestion API")

ALLOWED_ORIGINS = [
    "http://localhost:5173",
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


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/suggest", response_model=list[CandidateRule])
def suggest(req: SuggestRequest):
    config = load_llm_runtime_config()
    if not config.api_key:
        raise HTTPException(500, "BLABLADOR_API_KEY not configured on this Space")

    prompt = build_prompt(req)
    raw = call_blablador(prompt)
    return parse_candidates(raw)


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
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        },
        timeout=config.timeout_s,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def parse_candidates(raw: str) -> list[dict]:
    # Strip markdown code fences if the model added them despite instructions.
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise HTTPException(502, f"Could not parse model output as JSON: {e}")
