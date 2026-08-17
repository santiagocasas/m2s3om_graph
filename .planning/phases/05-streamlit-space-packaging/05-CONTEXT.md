# Phase 05: Unified Vite+FastAPI App Packaging - Context

**Gathered:** 2026-08-17
**Status:** Re-scoped after user feedback, ready for re-discuss/re-plan

## Phase Boundary

Unify the Vite explorer (Browse + Curate/Suggest) with a FastAPI backend into a single Hugging Face Space Docker image, add a new Convert-a-record page, keep GitLab Pages as a static, browse-only mirror, and keep Streamlit (`app/`) internal only, not packaged. Reuse existing Phases 02-04 code (Vite explorer, suggestion API scaffold, Blablador client) and extend with a new top-level `server/` FastAPI app that serves the built Vite SPA and provides `/health`, `/suggest`, and `/convert` endpoints. The Space must be deployable via Docker, configure via environment variables/secrets, and contain no runtime references to `claude_suggestions/` for the new app (the scaffold code is reused but relocated).

## Implementation Decisions

### Architecture Choices (locked by user)
- **D-01:** Unified app = Vite frontend + FastAPI backend, one Docker image for Hugging Face Spaces. No Streamlit packaging.
- **D-02:** GitLab Pages remains static, browse-only mirror of Vite build (Phases 02-04 unchanged).
- **D-03:** Streamlit (`app/`) stays in repo for internal/local use only, never packaged or deployed.
- **D-04:** New backend location: top-level `server/` (sibling to `app/` and `web/`). Reversibility: reversible.

### Backend Scope
- **D-05:** Promote existing suggestion API scaffold from `claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/main.py` into `server/`; preserve `/health` and `POST /suggest` with `SUGGEST_API_ALLOWED_ORIGINS` CORS config from Phase 03 D-05/D-06.
- **D-06:** Add new record-conversion endpoint `POST /convert` wrapping existing `src/m2s3om_graph/transform` logic (same capability as Streamlit's "Convert One Record" tab, but simplified linear flow). Reversibility: reversible.
- **D-07:** Backend imports from installed `m2s3om_graph` package, does not copy source.

### Frontend Scope
- **D-08:** Keep existing Vite explorer pages Browse and Curate/Suggest (Phases 02-04).
- **D-09:** Add new Vite page "Convert a record": linear flow (source paste/OAI-PMH → target standard → convert → result), no hidden step-gated state machine.
- **D-10:** Vite dev export path fixed to `web/public/data/crosswalk_graph.json` (Phase 05 re-scope item 0).

### Packaging
- **D-11:** Multi-stage Dockerfile: Node stage builds Vite `dist/`; Python `python:3.12-slim` stage installs FastAPI/uvicorn, serves static files via `StaticFiles`, listens on port 7860.
- **D-12:** Env-driven config carried forward: Blablador (`BLABLADOR_BASE_URL`, `BLABLADOR_MODEL`), SurrealDB vars (optional for future backend use), `SUGGEST_API_ALLOWED_ORIGINS`.
- **D-13:** Superseded Streamlit scaffold (`spaces/m2s3om-streamlit-space/`, `scripts/build_space_scaffold.sh`, `tests/test_space_scaffold.py`) removed (reverted commits eb05a4c, 739b2b1).

### the agent's Discretion
- Exact FastAPI static-file serving pattern, Vite build args, and Dockerfile user UID can be chosen by planner.
- Exact request/response schema for `/convert` can be defined in planning phase.

## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase and Requirements
- `.planning/ROADMAP.md` — Phase 05 goal, depends on Phase 04, success criteria 1-4 (updated)
- `.planning/REQUIREMENTS.md` — SPACE-01, SPACE-02 definitions
- `.planning/PROJECT.md` — Milestone v2.0 Deployment Surfaces context and constraints

### Existing Code to Reuse
- `web/src/main.js`, `web/index.html`, `web/src/curation.js`, `web/src/style.css` — Vite explorer and browser curation (Phases 02-04)
- `claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/main.py` — existing suggestion API scaffold to promote to `server/`
- `src/m2s3om_graph/transform/` — transform logic to wrap in `/convert` endpoint
- `src/m2s3om_graph/rdamsc/constants.py`, `src/m2s3om_graph/rdamsc/llm_runtime.py` — Blablador client config (Phase 03)
- `scripts/export_crosswalk_json.py` — now writes to `web/public/data/crosswalk_graph.json`
- `.gitlab-ci.yml` — pages job (updated export path)

### Local Run Context
- `README.md` — local env var examples for SurrealDB, Vite dev, Streamlit

## Existing Code Insights

### Reusable Assets
- Vite explorer (`web/`) with Browse and Curate/Suggest pages — reuse as-is.
- Suggestion API scaffold — promote to `server/` with same CORS/env handling.
- `src/m2s3om_graph/transform` — core conversion logic for new `/convert` endpoint.
- `scripts/export_crosswalk_json.py` — export path fixed to `web/public/data/`.

### Established Patterns
- Environment-driven config via `os.getenv` with sensible defaults.
- Vite dev server expects `VITE_SUGGEST_API_URL` and data at `public/data/crosswalk_graph.json`.
- FastAPI services expose `/health` and use `SUGGEST_API_ALLOWED_ORIGINS` for CORS.

### Integration Points
- Multi-stage Docker: Node builds `web/dist/` → FastAPI serves static files at root, API at `/api/*`.
- GitLab Pages serves static `web/dist/` copy, no backend.
- Streamlit remains local-only, no packaging.

## Specific Ideas

- Keep Dockerfile user `user` with UID 1000 as per scaffold.
- README should explicitly list Hugging Face Secrets names matching env vars.
- Avoid copying entire repo; copy only `app/`, `src/m2s3om_graph`, `exports/sssom`, `pyproject.toml`.

## Deferred Ideas

None — discussion stayed within phase scope.

---

*Phase: 05-Unified Vite+FastAPI App Packaging*
*Context gathered: 2026-08-17 (re-scoped)*
