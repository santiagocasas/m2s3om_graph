import json
import os
import re
import time

import requests

from kaigraph.db import MappingType


def configured_llm_model() -> str:
    return os.getenv("KAIGRAPH_LLM_MODEL", "alias-fast")


def blablador_enabled() -> bool:
    return bool(os.getenv("BLABLADOR_API_KEY"))


def _int_env(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(maximum, value))


def configured_llm_timeout_s() -> int:
    return _int_env("KAIGRAPH_LLM_TIMEOUT_S", 60, minimum=5, maximum=300)


def configured_llm_retries() -> int:
    return _int_env("KAIGRAPH_LLM_RETRIES", 2, minimum=0, maximum=6)


def configured_llm_max_input_chars() -> int:
    return _int_env(
        "KAIGRAPH_LLM_MAX_INPUT_CHARS", 120_000, minimum=2_000, maximum=300_000
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


def extract_mapping_candidates_with_meta(
    text: str,
    source_standard: str,
    target_standard: str,
    *,
    max_rules: int = 160,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    diagnostics: dict[str, object] = {
        "backend": "heuristic",
        "prompt_chars": 0,
        "llm_error": None,
        "candidates_before_validation": 0,
        "candidates_after_validation": 0,
        "timeout_s": configured_llm_timeout_s(),
        "retries": configured_llm_retries(),
        "max_input_chars": configured_llm_max_input_chars(),
        "attempts_json": 0,
        "attempts_relaxed": 0,
    }

    api_key = os.getenv("BLABLADOR_API_KEY")
    if not api_key:
        diagnostics["backend"] = "heuristic"
        diagnostics["llm_error"] = "missing_api_key"
        heuristic = _heuristic_extract(text, max_rules)
        diagnostics["candidates_after_validation"] = len(heuristic)
        return heuristic, diagnostics

    base_url = os.getenv(
        "BLABLADOR_BASE_URL",
        "https://api.helmholtz-blablador.fz-juelich.de/v1",
    ).rstrip("/")

    max_input_chars = int(diagnostics["max_input_chars"])
    excerpt = text[:max_input_chars]
    diagnostics["prompt_chars"] = len(excerpt)
    timeout_s = int(diagnostics["timeout_s"])
    retries = int(diagnostics["retries"])

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

    out: list[dict[str, object]] = []
    try:
        response, attempts = _request_with_retries(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            payload=payload,
            timeout_s=timeout_s,
            retries=retries,
        )
        diagnostics["attempts_json"] = attempts
        raw = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(_clean_json_blob(raw))
        if isinstance(parsed, list):
            diagnostics["candidates_before_validation"] = len(parsed)
            for item in parsed:
                if not isinstance(item, dict):
                    continue
                source = str(item.get("source_path", "")).strip()
                target = str(item.get("target_path", "")).strip()
                if not source:
                    continue
                mapping_type = _validate_mapping_type(
                    str(item.get("mapping_type", "direct"))
                )
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
    except Exception as exc:
        diagnostics["llm_error"] = str(exc)

    if out:
        diagnostics["backend"] = "llm_json"
        diagnostics["candidates_after_validation"] = len(out)
        return out, diagnostics

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
                    f"target_standard={target_standard}\n\n" + excerpt
                ),
            },
        ],
    }
    try:
        response, attempts = _request_with_retries(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            payload=relaxed_payload,
            timeout_s=timeout_s,
            retries=retries,
        )
        diagnostics["attempts_relaxed"] = attempts
        raw = str(response.json()["choices"][0]["message"]["content"])
        raw_lines = [line for line in raw.splitlines() if line.strip()]
        diagnostics["candidates_before_validation"] = len(raw_lines)
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
