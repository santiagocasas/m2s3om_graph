import json
import os
import re

import requests

from kaigraph.db import MappingType


def configured_llm_model() -> str:
    return os.getenv("KAIGRAPH_LLM_MODEL", "alias-fast")


def blablador_enabled() -> bool:
    return bool(os.getenv("BLABLADOR_API_KEY"))


def _clean_json_blob(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?", "", stripped).strip()
        stripped = re.sub(r"```$", "", stripped).strip()
    return stripped


def _validate_mapping_type(raw: str) -> MappingType:
    try:
        return MappingType(raw)
    except ValueError:
        return MappingType.DIRECT


def _heuristic_extract(text: str, max_rules: int) -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    patterns = [
        re.compile(r"^\s*([A-Za-z0-9_:.\-\s]+?)\s*->\s*([A-Za-z0-9_:.\-\s]+?)\s*$"),
        re.compile(r"^\s*([A-Za-z0-9_:.\-\s]+?)\s*=>\s*([A-Za-z0-9_:.\-\s]+?)\s*$"),
    ]
    for line in text.splitlines():
        for pattern in patterns:
            match = pattern.match(line)
            if match is None:
                continue
            source = match.group(1).strip()
            target = match.group(2).strip()
            if not source or not target:
                continue
            out.append(
                {
                    "source_path": source,
                    "target_path": target,
                    "mapping_type": "direct",
                    "confidence": 0.55,
                    "notes": "Heuristic pattern extraction",
                    "evidence": line.strip(),
                }
            )
            if len(out) >= max_rules:
                return out
    return out


def extract_mapping_candidates(
    text: str,
    source_standard: str,
    target_standard: str,
    *,
    max_rules: int = 160,
) -> list[dict[str, object]]:
    api_key = os.getenv("BLABLADOR_API_KEY")
    base_url = os.getenv(
        "BLABLADOR_BASE_URL",
        "https://api.helmholtz-blablador.fz-juelich.de/v1",
    ).rstrip("/")

    if not api_key:
        return _heuristic_extract(text, max_rules)

    prompt_payload = {
        "source_standard": source_standard,
        "target_standard": target_standard,
        "max_rules": max_rules,
        "documentation_excerpt": text[:120_000],
        "output_schema": {
            "type": "array",
            "items": {
                "source_path": "string",
                "target_path": "string",
                "mapping_type": "direct|conditional|aggregation|decomposition|missing",
                "confidence": "float 0..1",
                "notes": "string",
                "evidence": "short snippet",
            },
        },
    }

    payload = {
        "model": configured_llm_model(),
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You extract metadata crosswalk rules from documentation. "
                    "Return ONLY valid JSON matching the requested schema. "
                    "Do not include markdown fences."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(prompt_payload, ensure_ascii=True),
            },
        ],
    }

    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=60,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(_clean_json_blob(raw))
        if not isinstance(parsed, list):
            return _heuristic_extract(text, max_rules)
    except Exception:
        return _heuristic_extract(text, max_rules)

    out: list[dict[str, object]] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        source = str(item.get("source_path", "")).strip()
        target = str(item.get("target_path", "")).strip()
        if not source:
            continue
        mapping_type = _validate_mapping_type(str(item.get("mapping_type", "direct")))
        try:
            confidence = float(item.get("confidence", 0.6))
        except (TypeError, ValueError):
            confidence = 0.6
        confidence = max(0.0, min(1.0, confidence))
        out.append(
            {
                "source_path": source,
                "target_path": target,
                "mapping_type": mapping_type.value,
                "confidence": confidence,
                "notes": str(item.get("notes", "")).strip() or None,
                "evidence": str(item.get("evidence", "")).strip() or None,
            }
        )
        if len(out) >= max_rules:
            break

    if out:
        return out

    relaxed_payload = {
        "model": configured_llm_model(),
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Extract any likely source-target mapping pairs from the provided "
                    "documentation text. Output only TSV lines with three columns: "
                    "source_path<TAB>target_path<TAB>short evidence."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"source_standard={source_standard}\n"
                    f"target_standard={target_standard}\n\n" + text[:120_000]
                ),
            },
        ],
    }
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=relaxed_payload,
            timeout=60,
        )
        response.raise_for_status()
        raw = str(response.json()["choices"][0]["message"]["content"])
        for line in raw.splitlines():
            parts = [x.strip() for x in line.split("\t")]
            if len(parts) < 2:
                continue
            source = parts[0]
            target = parts[1]
            if not source or not target:
                continue
            evidence = parts[2] if len(parts) > 2 else "LLM relaxed extraction"
            out.append(
                {
                    "source_path": source,
                    "target_path": target,
                    "mapping_type": "direct",
                    "confidence": 0.45,
                    "notes": "Relaxed LLM extraction",
                    "evidence": evidence,
                }
            )
            if len(out) >= max_rules:
                break
    except Exception:
        return _heuristic_extract(text, max_rules)

    if out:
        return out
    return _heuristic_extract(text, max_rules)
