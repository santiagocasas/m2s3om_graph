# Phase 03: Suggestion API Integration - Context

**Gathered:** 2026-08-15
**Status:** Ready for planning

## Phase Boundary

Wire the suggestion API scaffold to the repository's existing Blablador client used by the extraction pipeline, while keeping the public API surface stable. Replace the scaffold's mocked Blablador call with the real client. Preserve `call_blablador(prompt: str) -> str` signature. Ensure `BLABLADOR_BASE_URL` and `BLABLADOR_MODEL` defaults match existing pipeline defaults or are corrected with evidence. Do not guess `ALLOWED_ORIGINS`; surface unresolved production Pages URL decisions. Mocked-LLM tests must confirm `/health` and `/suggest` still work after wiring.

## Implementation Decisions

### API surface stability
- **D-01:** `call_blablador(prompt: str) -> str` signature must be preserved exactly as defined in scaffold `claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/main.py:93`. Delegation to existing client must be via adapter, not signature change. — **Reversibility:** one-way — changing the public signature would break the `/suggest` endpoint contract and downstream frontend integration.
- **D-02:** `BLABLADOR_BASE_URL` default must match existing pipeline default `https://api.helmholtz-blablador.fz-juelich.de/v1` from `src/m2s3om_graph/rdamsc/constants.py:7`. Evidence: `BLABLADOR_DEFAULT_BASE_URL` defined as `https://api.helmholtz-blablador.fz-juelich.de/v1`. — **Reversibility:** reversible — env override supported.
- **D-03:** `BLABLADOR_MODEL` default must match existing pipeline default `alias-fast`. Evidence: `src/m2s3om_graph/rdamsc/llm_runtime.py:7` defines `DEFAULT_LLM_MODEL = "alias-fast"` and `load_llm_runtime_config` uses `M2S3OM_LLM_MODEL` env with that default. — **Reversibility:** reversible.

### Client reuse
- **D-04:** Use existing Blablador client configuration from `src/m2s3om_graph/rdamsc/llm_runtime.py` and `src/m2s3om_graph/rdamsc/constants.py`. The existing client loads `BLABLADOR_API_KEY`, `BLABLADOR_BASE_URL`, `M2S3OM_LLM_MODEL`, timeout, retries via `load_llm_runtime_config()`. — **Reversibility:** costly — changing config source would require updating multiple pipeline consumers.
- **D-05:** `ALLOWED_ORIGINS` must not be guessed. Scaffold currently hardcodes `["http://localhost:5173"]` in `claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/main.py:18-20`. Production GitLab Pages URL is unresolved; decision deferred to user. Do not add production URL without explicit confirmation. — **Reversibility:** reversible.

### Prompt / message format
- **D-06:** Gray area — Prompt adaptation strategy. Scaffold `call_blablador` sends prompt as raw user message with temperature 0.2. Existing pipeline client sends structured messages with system prompt and JSON payload, temperature 0. User decision required on whether to:
  a) Create a thin generic LLM call using `llm_runtime` config that forwards the prompt as user message preserving scaffold behavior, or
  b) Adapt scaffold prompts to existing candidate suggestion format. This impacts temperature and message shape.

### Error handling
- **D-07:** `call_blablador` must retain FastAPI error semantics from scaffold: raise `HTTPException(500)` when `BLABLADOR_API_KEY` not configured, raise `HTTPException(502)` on JSON parse failure. Existing client returns heuristic fallback when API key missing; this divergence must be reconciled.

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requirements
- `.planning/ROADMAP.md` §Phase 03 — Goal, success criteria, dependencies
- `.planning/REQUIREMENTS.md` §API-01, API-02 — Signature preservation, mocked-LLM tests
- `.planning/PROJECT.md` §Current Milestone — Integration governance

### Scaffold
- `claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/main.py` — Existing scaffold with `call_blablador`, `ALLOWED_ORIGINS`, defaults
- `claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/README.md` — Setup notes and TODOs for replacing `call_blablador`

### Existing Blablador client
- `src/m2s3om_graph/rdamsc/constants.py` — `BLABLADOR_DEFAULT_BASE_URL`, `BLABLADOR_HOST`
- `src/m2s3om_graph/rdamsc/llm_runtime.py` — `load_llm_runtime_config`, `DEFAULT_LLM_MODEL`, `llm_chat_completions_url`, env vars
- `src/m2s3om_graph/candidates/blablador.py` — Existing usage pattern for Blablador client with `load_llm_runtime_config`, payload shape, temperature 0, system+user messages

### Tests
- `tests/test_rdamsc_llm_runtime.py` — Validates defaults and env handling
- `tests/test_candidates.py` — Validates heuristic fallback and error recording

## Existing Code Insights

### Reusable Assets
- `llm_runtime.load_llm_runtime_config()` — Centralized config loading for Blablador API key, base URL, model, timeout, retries.
- `llm_runtime.llm_chat_completions_url(config)` — Builds `/{base}/chat/completions` URL.
- `candidates.blablador.suggest_candidate_mappings` — Example adapter pattern using `requests.post` with Authorization Bearer, model, temperature 0, system+user messages.

### Established Patterns
- Pipeline uses environment variables: `BLABLADOR_API_KEY`, `BLABLADOR_BASE_URL`, `M2S3OM_LLM_MODEL`, `M2S3OM_LLM_TIMEOUT_S`.
- Default base URL is `https://api.helmholtz-blablador.fz-juelich.de/v1`.
- Default model is `alias-fast`.
- When API key missing, existing client falls back to heuristic suggestions; scaffold raises HTTP 500.

### Integration Points
- Scaffold `main.py` `suggest` endpoint builds prompt via `build_prompt(req)` and calls `call_blablador(prompt)`.
- Replacement must keep `/health` and `/suggest` endpoints unchanged.
- CORS middleware uses `ALLOWED_ORIGINS`; production URL unknown.

## Specific Ideas

- No specific UI preferences; API-only phase.
- User explicitly requested no guessing for `ALLOWED_ORIGINS`.

## Deferred Ideas

None — discussion stayed within phase scope.

---
*Phase: 03-Suggestion API Integration*
*Context gathered: 2026-08-15*
