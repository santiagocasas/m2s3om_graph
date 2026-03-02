import json
import os
from dataclasses import dataclass

import requests


@dataclass
class CandidateSuggestion:
    target_path: str
    confidence: float
    rationale: str


def _tokenize(text: str) -> set[str]:
    out: set[str] = set()
    for raw in text.lower().replace("_", " ").replace(".", " ").split():
        token = "".join(ch for ch in raw if ch.isalnum())
        if token:
            out.add(token)
    return out


def _heuristic_suggestions(
    source_text: str,
    target_paths: list[str],
    max_candidates: int,
) -> list[CandidateSuggestion]:
    src_tokens = _tokenize(source_text)
    scored: list[tuple[str, float]] = []
    for target in target_paths:
        tgt_tokens = _tokenize(target)
        if not src_tokens or not tgt_tokens:
            score = 0.0
        else:
            score = len(src_tokens & tgt_tokens) / len(src_tokens | tgt_tokens)
        scored.append((target, score))
    scored.sort(key=lambda x: (-x[1], x[0]))
    result: list[CandidateSuggestion] = []
    for target, score in scored[:max_candidates]:
        result.append(
            CandidateSuggestion(
                target_path=target,
                confidence=round(min(0.79, 0.35 + score), 3),
                rationale="Heuristic lexical overlap (non-authoritative candidate).",
            )
        )
    return result


def suggest_candidate_mappings(
    source_text: str,
    target_paths: list[str],
    max_candidates: int = 3,
) -> list[CandidateSuggestion]:
    api_key = os.getenv("BLABLADOR_API_KEY")
    base_url = os.getenv(
        "BLABLADOR_BASE_URL",
        "https://api.helmholtz-blablador.fz-juelich.de/v1",
    ).rstrip("/")
    if not api_key:
        return _heuristic_suggestions(source_text, target_paths, max_candidates)

    payload = {
        "model": os.getenv("KAIGRAPH_LLM_MODEL", "alias-fast"),
        "temperature": 0,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You suggest non-authoritative metadata crosswalk candidates. "
                    "Return strict JSON list with keys target_path, confidence, rationale."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "source_text": source_text,
                        "target_paths": target_paths,
                        "max_candidates": max_candidates,
                    }
                ),
            },
        ],
    }
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
            timeout=20,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        parsed = json.loads(raw)
        suggestions: list[CandidateSuggestion] = []
        if isinstance(parsed, list):
            for item in parsed[:max_candidates]:
                if not isinstance(item, dict):
                    continue
                target = str(item.get("target_path", "")).strip()
                if not target:
                    continue
                confidence = float(item.get("confidence", 0.5))
                suggestions.append(
                    CandidateSuggestion(
                        target_path=target,
                        confidence=max(0.0, min(1.0, confidence)),
                        rationale=str(
                            item.get("rationale", "LLM candidate suggestion")
                        ),
                    )
                )
        if suggestions:
            return suggestions
    except Exception:
        pass
    return _heuristic_suggestions(source_text, target_paths, max_candidates)
