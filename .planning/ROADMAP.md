# Roadmap: m2s3om_graph v2.0 Deployment Surfaces

**Milestone:** v2.0 Deployment Surfaces
**Created:** 2026-06-17
**Phase numbering:** Continues from previous completed Phase 01

## Milestone Goal

Integrate the reference deployment and curation scaffolds into the existing codebase without creating parallel implementations.

## Phase Overview

| Phase | Name | Goal | Requirements | Success Criteria |
|-------|------|------|--------------|------------------|
| 02 | Static Frontend Data Export | Orient in the current repo, export real crosswalk data, and integrate the Vite GitLab Pages explorer into the canonical Pages source. | DATA-01, WEB-01, WEB-02, GOV-01 | 5 (3 plans) |
| 03 | Suggestion API Integration | Wire the suggestion API scaffold to the existing Blablador client while preserving its public API behavior and mocked tests. | API-01, API-02 | 4 |
| 04 | Browser Curation Workflow | Add suggestion-driven curation to the static explorer with browser-memory decisions and TSV export only. | CUR-01, CUR-02, CUR-03 | 4 |
| 05 | Streamlit Space Packaging | Package the existing Streamlit app into the Hugging Face Space scaffold with environment-based runtime configuration. | SPACE-01, SPACE-02 | 4 |

## Phase Details

### Phase 02: Static Frontend Data Export

**Goal:** Orient in the repository, integrate the static frontend scaffold into the canonical GitLab Pages source, and feed it real exported data.

**Depends on:** Phase 01

**Requirements:** DATA-01, WEB-01, WEB-02, GOV-01

**UI hint:** yes

**Success criteria:**
1. The implementation has read the existing Pages setup, Streamlit/SurrealDB wiring, Blablador client, SSSOM TSV storage, standards list, and all three scaffold folders before code changes.
2. A Python export script in the existing pipeline codebase writes JSON with `standards[]`, `crosswalks[]`, and nested `rules[]` from committed SSSOM TSVs and standards data.
3. The Vite explorer lives in the canonical Pages source, loads the real exported JSON, and does not depend on `claude_suggestions/` sample data.
4. `.gitlab-ci.yml` has exactly one `pages` job after merging the scaffold CI snippet.
5. Local `npm install` and `npm run build` succeed and produce `dist/` before the phase is committed.

**Plans:** 3 plans

Plans:
- [ ] 02-01-PLAN.md — Tracer: end-to-end SSSOM→JSON→Vite→CI slice with pinned deps and test scaffolds
- [ ] 02-02-PLAN.md — Rich audit export: full D-02 fields, strategy inference, header-driven standards, collision validation
- [ ] 02-03-PLAN.md — Frontend polish: six-column table, strategy badges, ID escaping, nav integration

### Phase 03: Suggestion API Integration

**Goal:** Replace the scaffold's mocked Blablador call with the repository's existing Blablador client while keeping the API surface stable.

**Depends on:** Phase 02

**Requirements:** API-01, API-02

**UI hint:** no

**Success criteria:**
1. `call_blablador(prompt: str) -> str` keeps the same signature and delegates to the existing extraction-pipeline Blablador client.
2. `BLABLADOR_BASE_URL` and `BLABLADOR_MODEL` defaults match the existing pipeline defaults or are corrected with evidence.
3. `ALLOWED_ORIGINS` is not guessed; unresolved production Pages URL decisions are surfaced to the user.
4. Mocked-LLM tests confirm `/health` and `/suggest` still work after wiring in the real client.

### Phase 04: Browser Curation Workflow

**Goal:** Let curators request and review candidate mappings in the static explorer without writing back to authoritative files.

**Depends on:** Phase 03

**Requirements:** CUR-01, CUR-02, CUR-03

**UI hint:** yes

**Success criteria:**
1. The static explorer shows "Suggest candidate mappings" only for source fields with no existing rule in the selected crosswalk.
2. The button posts to the suggestion API `/suggest` endpoint and renders returned candidates.
3. Curators can accept or reject candidates in browser memory for the current session.
4. Accepted candidates can be exported as `accepted_candidates.tsv`, and the UI does not imply automatic write-back to authoritative SSSOM files.

### Phase 05: Streamlit Space Packaging

**Goal:** Turn the Streamlit Space scaffold into a deployable wrapper around the existing Streamlit app with environment-driven configuration.

**Depends on:** Phase 02

**Requirements:** SPACE-01, SPACE-02

**UI hint:** no

**Success criteria:**
1. The Space scaffold contains the existing Streamlit entrypoint, supporting modules, requirements, Dockerfile, and README in the final location.
2. Hardcoded localhost addresses and local file paths, especially SurrealDB connection settings, are replaced with `os.environ.get(...)` configuration.
3. The Space README lists required Hugging Face Secrets/environment variables.
4. The package does not import from or point runtime behavior at `claude_suggestions/`.

## Coverage

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 02 | Pending |
| WEB-01 | Phase 02 | Pending |
| WEB-02 | Phase 02 | Pending |
| API-01 | Phase 03 | Pending |
| API-02 | Phase 03 | Pending |
| CUR-01 | Phase 04 | Pending |
| CUR-02 | Phase 04 | Pending |
| CUR-03 | Phase 04 | Pending |
| SPACE-01 | Phase 05 | Pending |
| SPACE-02 | Phase 05 | Pending |
| GOV-01 | Phase 02 | Pending |

**Coverage:**
- v2.0 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0

---
*Roadmap created: 2026-06-17 for milestone v2.0 Deployment Surfaces*
