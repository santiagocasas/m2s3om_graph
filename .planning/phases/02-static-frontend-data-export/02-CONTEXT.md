# Phase 02: Static Frontend Data Export

**Milestone:** v2.0 Deployment Surfaces  
**Phase:** 02 Static Frontend Data Export  
**Status:** Discuss complete  
**Last updated:** 2026-08-14

## Phase Goal
Orient in the repository, integrate the static frontend scaffold into the canonical GitLab Pages source, and feed it real exported data.

## Dependencies
- Phase 01 complete
- Existing Pages setup, Streamlit/SurrealDB wiring, Blablador client, SSSOM TSV storage, standards list
- Scaffold folders reviewed but not reused as runtime dependencies

## Requirements
- DATA-01
- WEB-01
- WEB-02
- GOV-01

## Success Criteria
1. Repository orientation complete before code changes.
2. Python export script writes JSON with `standards[]`, `crosswalks[]`, and nested `rules[]` from committed SSSOM TSVs and standards data.
3. Vite explorer lives in canonical Pages source, loads real exported JSON, does not depend on `claude_suggestions/` sample data.
4. `.gitlab-ci.yml` has exactly one `pages` job after merging scaffold CI snippet.
5. Local `npm install` and `npm run build` succeed and produce `dist/` before phase commit.

## Decisions Captured

### Site integration
- Explorer exposed as dedicated page under `explorer/`.
- Header navigation plus overview card entry point.
- Existing `docs/pages` shell remains authoritative; Vite explorer is a separate interactive surface.
- Visual style: reuse shell language, separate app styling.
- Failure mode: visible fail-closed state with expected data path and build guidance.

### Data contract
- Export rich audit record per rule.
- Fields: source/target paths as arrays, display labels, mapping type, confidence, semantic-loss flag, ambiguity flag, transform/notes, strategy, provenance fields.
- Strategy field explicitly labels `deterministic`, `llm`, or `fallback`.
- Evidence includes structured provenance plus source link/citation/chunk identifiers where available.
- Multi-path mappings preserved as arrays with derived display strings.
- Missing/non-mappable rules included as explicit records with semantic-loss flag and empty target paths.

### Graph identifiers
- Display canonical ID and human label.
- Browser-local SurrealDB keys derived via deterministic encoding from canonical ID; original ID retained.
- Collision handling: build-time error preferred; user chose stable hash suffix as disambiguation.
- Explorer and graph pages linked by canonical ID for auditability.

### Build orchestration
- Sequence: export/validate data → build Python Pages site → build Vite explorer into `public/explorer/`.
- Pages job uses pinned Node image and lockfile; Python generation retained.
- Failure policy: warn but publish; explorer failure visible, site remains available.
- Developer command: one documented command that validates/exports data and produces complete `public/` artifact.

## Constraints
- Write operations were read-only during initial discussion; context now persisted.
- `claude_suggestions/` is reference-only.
- No parallel implementations; integrate under existing `docs/pages`.

## Open Questions / Risks
- Exact shape of `strategy` metadata in existing graph/pipeline; needs mapping from pipeline stats.
- Source of citation/chunk identifiers for evidence; confirm availability in current SSSOM comments.
- SurrealDB WASM usage vs static JSON; current decisions favor static JSON export with SurrealDB for browser runtime only.
- Node toolchain pinning for CI and local reproducibility.

## Next Steps
1. Create plan via `/gsd-plan-phase 02`.
2. Implement export script to generate `standards.json`, `crosswalks.json` with rich audit schema.
3. Integrate Vite explorer under `docs/pages/explorer/`.
4. Update `.gitlab-ci.yml` to single `pages` job with Python + Vite steps.
5. Add documented local build command.
