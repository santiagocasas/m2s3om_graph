import json
import re
import time

import requests

from kaigraph.db import MappingType

from .contracts import LLMDiagnostics, llm_diagnostics_template
from .llm_runtime import (
    llm_chat_completions_url_from_base,
    llm_enabled,
    load_llm_runtime_config,
)


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


def _normalize_json_candidate(item: object) -> dict[str, object] | None:
    if not isinstance(item, dict):
        return None
    source = str(item.get("source_path", "")).strip()
    target = str(item.get("target_path", "")).strip()
    if not source:
        return None
    mapping_type = _validate_mapping_type(str(item.get("mapping_type", "direct")))
    try:
        confidence = float(item.get("confidence", 0.6))
    except (TypeError, ValueError):
        confidence = 0.6
    confidence = max(0.0, min(1.0, confidence))
    return {
        "source_path": source,
        "target_path": target,
        "mapping_type": mapping_type.value,
        "confidence": confidence,
        "notes": str(item.get("notes", "")).strip() or None,
        "evidence": str(item.get("evidence", "")).strip() or None,
    }


def _request_with_retries(
    url: str,
    *,
    headers: dict[str, str],
    payload: dict[str, object],
    timeout_s: int,
    retries: int,
) -> tuple[requests.Response, int]:
    errors: list[str] = []
    for attempt in range(retries + 1):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=payload,
                timeout=timeout_s,
            )
            response.raise_for_status()
            return response, attempt + 1
        except requests.RequestException as exc:
            errors.append(str(exc))
            if attempt >= retries:
                break
            time.sleep(0.35 * (attempt + 1))
    message = errors[-1] if errors else "unknown network error"
    raise RuntimeError(message)


def _extract_json_mode(
    *,
    base_url: str,
    api_key: str,
    payload: dict[str, object],
    timeout_s: int,
    retries: int,
    max_rules: int,
) -> tuple[list[dict[str, object]], int, int]:
    endpoint = llm_chat_completions_url_from_base(base_url)
    response, attempts = _request_with_retries(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
        payload=payload,
        timeout_s=timeout_s,
        retries=retries,
    )

    raw = response.json()["choices"][0]["message"]["content"]
    try:
        parsed = json.loads(_clean_json_blob(raw))
    except json.JSONDecodeError:
        return [], attempts, 0
    if not isinstance(parsed, list):
        return [], attempts, 0

    out: list[dict[str, object]] = []
    for item in parsed:
        candidate = _normalize_json_candidate(item)
        if candidate is None:
            continue
        out.append(candidate)
        if len(out) >= max_rules:
            break

    return out, attempts, len(parsed)


def _extract_relaxed_mode(
    *,
    base_url: str,
    api_key: str,
    payload: dict[str, object],
    timeout_s: int,
    retries: int,
    max_rules: int,
) -> tuple[list[dict[str, object]], int, int]:
    endpoint = llm_chat_completions_url_from_base(base_url)
    response, attempts = _request_with_retries(
        endpoint,
        headers={"Authorization": f"Bearer {api_key}"},
        payload=payload,
        timeout_s=timeout_s,
        retries=retries,
    )

    raw = str(response.json()["choices"][0]["message"]["content"])
    raw_lines = [line for line in raw.splitlines() if line.strip()]
    out: list[dict[str, object]] = []
    for line in raw_lines:
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

    return out, attempts, len(raw_lines)


def extract_mapping_candidates_with_meta(
    text: str,
    source_standard: str,
    target_standard: str,
    *,
    max_rules: int = 160,
) -> tuple[list[dict[str, object]], LLMDiagnostics]:
    config = load_llm_runtime_config()
    diagnostics = llm_diagnostics_template(
        timeout_s=config.timeout_s,
        retries=config.retries,
        max_input_chars=config.max_input_chars,
    )

    if not llm_enabled(config):
        diagnostics["backend"] = "heuristic"
        diagnostics["llm_error"] = "missing_api_key"
        heuristic = _heuristic_extract(text, max_rules)
        diagnostics["candidates_after_validation"] = len(heuristic)
        return heuristic, diagnostics

    excerpt = text[: config.max_input_chars]
    diagnostics["prompt_chars"] = len(excerpt)
    timeout_s = config.timeout_s
    retries = config.retries

    prompt_payload = {
        "source_standard": source_standard,
        "target_standard": target_standard,
        "max_rules": max_rules,
        "documentation_excerpt": excerpt,
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
        "model": config.model,
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

    out: list[dict[str, object]] = []
    try:
        out, attempts, before_validation = _extract_json_mode(
            base_url=config.base_url,
            api_key=config.api_key,
            payload=payload,
            timeout_s=timeout_s,
            retries=retries,
            max_rules=max_rules,
        )
        diagnostics["attempts_json"] = attempts
        diagnostics["candidates_before_validation"] = before_validation
    except Exception as exc:
        diagnostics["llm_error"] = str(exc)

    if out:
        diagnostics["backend"] = "llm_json"
        diagnostics["candidates_after_validation"] = len(out)
        return out, diagnostics

    relaxed_payload = {
        "model": config.model,
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
                    f"target_standard={target_standard}\n\n" + excerpt
                ),
            },
        ],
    }
    try:
        out, attempts, before_validation = _extract_relaxed_mode(
            base_url=config.base_url,
            api_key=config.api_key,
            payload=relaxed_payload,
            timeout_s=timeout_s,
            retries=retries,
            max_rules=max_rules,
        )
        diagnostics["attempts_relaxed"] = attempts
        diagnostics["candidates_before_validation"] = before_validation
    except Exception as exc:
        diagnostics["llm_error"] = str(exc)

    if out:
        diagnostics["backend"] = "llm_relaxed"
        diagnostics["candidates_after_validation"] = len(out)
        return out, diagnostics

    diagnostics["backend"] = "heuristic"
    heuristic = _heuristic_extract(text, max_rules)
    diagnostics["candidates_after_validation"] = len(heuristic)
    return heuristic, diagnostics


def extract_mapping_candidates(
    text: str,
    source_standard: str,
    target_standard: str,
    *,
    max_rules: int = 160,
) -> list[dict[str, object]]:
    candidates, _ = extract_mapping_candidates_with_meta(
        text,
        source_standard,
        target_standard,
        max_rules=max_rules,
    )
    return candidates
