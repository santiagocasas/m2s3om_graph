# Phase 04: Browser Curation Workflow - Context

**Gathered:** 2026-08-16
**Status:** Ready for planning

## Phase Boundary

Let curators request and review candidate mappings in the static explorer without writing back to authoritative files. The explorer must show a "Suggest candidate mappings" action only for source fields with no existing rule in the selected crosswalk, post to the suggestion API `/suggest` endpoint, render returned candidates, and allow accept/reject decisions to be kept in browser memory for the current session with optional export to `accepted_candidates.tsv`. No write-back to authoritative SSSOM files or implication of automatic write-back is permitted.

## Implementation Decisions

### Explorer UI integration
- **D-01:** The Suggest button is rendered per source-field row only when `target_paths` is empty / missing for the rule. This matches CUR-01 requirement that the action appears only for source fields with no existing rule in the selected crosswalk. — **Reversibility:** reversible — button visibility logic can be adjusted without schema changes.
- **D-02:** The static explorer currently lives in `web/` with Vite build, SurrealDB WASM runtime, and data loaded from `data/crosswalk_graph.json` via `loadGraphData`. The existing table renders six columns: source, target, mapping_type, confidence, strategy badge, semantic loss. The Suggest UI will extend this table, not replace it. — **Reversibility:** reversible — additive UI change.
- **D-03:** Button posts a `SuggestRequest` payload to `/suggest` containing `source_standard`, `target_standard`, `source_field`, `target_schema_fields`, and optional `context`. Payload shape is defined by the suggestion API scaffold `claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/main.py`. — **Reversibility:** one-way — changing the request schema would break the stable `/suggest` contract established in Phase 03.

### Suggestion API consumption
- **D-04:** The frontend will call the `/suggest` endpoint with CORS allowed origins configured via `SUGGEST_API_ALLOWED_ORIGINS`. Production Pages URL is unresolved per Phase 03 D-05; frontend must not assume production origin. — **Reversibility:** reversible — env-driven.
- **D-05:** Candidates returned as `CandidateRule` objects with fields `source_path`, `target_path`, `mapping_type`, `confidence`, `evidence`, `notes`. Rendering will display these fields and provide Accept/Reject controls. — **Reversibility:** reversible.

### Browser state handling
- **D-06:** Accept/Reject decisions are kept in browser memory for the current session only, as required by CUR-02 and CUR-03. No persistence to SurrealDB WASM or IndexedDB is permitted for curation decisions; only the original crosswalk data is persisted. — **Reversibility:** one-way — introducing persistence would violate the no-write-back constraint.
- **D-07:** Export of accepted candidates is implemented as client-side TSV generation downloaded as `accepted_candidates.tsv`. The UI must explicitly state that export is manual and does not write back to authoritative SSSOM files. — **Reversibility:** reversible.

### the agent's Discretion
- Specific rendering style for candidate modal / inline expansion, loading states, and error messages for `/suggest` failures can be chosen by the implementer within the existing design language established in Phase 02 UI spec.

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Roadmap & requirements
- `.planning/ROADMAP.md` §Phase 04 — Goal, success criteria, dependencies
- `.planning/REQUIREMENTS.md` §CUR-01, CUR-02, CUR-03 — Curation UI requirements
- `.planning/PROJECT.md` §Current Milestone — Integration governance

### Prior phase context
- `.planning/phases/02-static-frontend-data-export/02-CONTEXT.md` — Explorer integration, data contract, SurrealDB WASM usage
- `.planning/phases/02-static-frontend-data-export/02-UI-SPEC.md` — Six-column table, strategy badges, ID escaping, nav integration
- `.planning/phases/03-suggestion-api-integration/03-CONTEXT.md` — API surface stability, `call_blablador` signature, `ALLOWED_ORIGINS` unresolved

### Scaffold & existing code
- `web/src/main.js` — Current explorer rendering logic, SurrealDB WASM initialization, `renderRules` implementation
- `web/index.html` — Controls, status, rules table markup
- `web/src/graph-loader.js` — SurrealDB loadGraphData, ID escaping
- `claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/main.py` — `/suggest` endpoint, `SuggestRequest`, `CandidateRule`, `call_blablador` signature
- `claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/README.md` — Setup notes
- `src/m2s3om_graph/rdamsc/llm_runtime.py` — `load_llm_runtime_config`, `DEFAULT_LLM_MODEL`
- `src/m2s3om_graph/rdamsc/constants.py` — `BLABLADOR_DEFAULT_BASE_URL`

### Tests
- `tests/test_suggest_api.py` — Mocked-LLM tests for `/health` and `/suggest`

## Existing Code Insights

### Reusable Assets
- `web/src/main.js` `renderRules` — Table row generation with source/target display, confidence formatting, strategy badge, semantic loss icon. Can be extended to include Suggest button column.
- `web/src/graph-loader.js` `escapeId` — SurrealDB record ID escaping for standards and crosswalks.
- `Surreal` WASM instance with `indxdb://m2s3om` — Browser-local persistence for crosswalk data; curation decisions must not be written here.
- `src/m2s3om_graph/candidates/blablador.py` `suggest_candidate_mappings` — Existing adapter pattern for Blablador calls, useful for understanding prompt shape.

### Established Patterns
- Vite build outputs to `dist/` and is published via GitLab Pages single `pages` job.
- Export script produces `standards[]`, `crosswalks[]`, nested `rules[]` JSON matching scaffold README shape.
- Frontend runs entirely client-side with no server except suggestion API.
- CORS is env-driven via `SUGGEST_API_ALLOWED_ORIGINS`; production origin not guessed.

### Integration Points
- Browser → `/suggest` FastAPI endpoint — Untrusted JSON body `SuggestRequest`; CORS-gated.
- `/suggest` service → Blablador HTTPS API — Server-to-external call with API key.
- Explorer → SurrealDB WASM — Read-only data loading; curation state stays in memory.

## Specific Ideas

- No specific UI layout preference captured beyond existing six-column table. Accept/Reject controls can be inline or modal.
- User emphasized no write-back to authoritative files; UI must make manual export explicit.

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 04-Browser Curation Workflow*
*Context gathered: 2026-08-16*
