# Requirements: m2s3om_graph v2.1 Unified Explorer — Graph + Stats Pages

**Defined:** 2026-08-25
**Core Value:** Enable cross-walking between metadata standards by providing machine-readable mapping rules that can be applied automatically while tracking semantic loss.

## v2.0 Requirements

Requirements for the Deployment Surfaces milestone. Each requirement maps to exactly one roadmap phase.

### Data Export

- [x] **DATA-01**: Maintainer can run a Python export script in the existing pipeline codebase that reads committed SSSOM TSV files plus the standards list and writes static-site JSON matching the scaffold README shape: `standards[]`, `crosswalks[]`, and nested `rules[]`.

### Static Frontend

- [x] **WEB-01**: User can open the GitLab Pages crosswalk explorer built from the integrated Vite scaffold in the repository's canonical Pages source, using the real exported JSON instead of the scaffold sample data.
- [x] **WEB-02**: Maintainer can run the local static frontend build successfully with `npm install` and `npm run build`, and GitLab CI contains exactly one `pages` job for publishing the site.

### Suggestion API

- [x] **API-01**: The suggestion API keeps the existing `call_blablador(prompt: str) -> str` signature while delegating to the repository's existing Blablador client and matching its default base URL/model settings.
- [x] **API-02**: Maintainer can run mocked-LLM tests confirming `/health` and `/suggest` still work after the real Blablador client is wired in.

### Curation UI

- [x] **CUR-01**: Curator sees a "Suggest candidate mappings" action only for source fields that have no existing rule in the currently selected crosswalk.
- [x] **CUR-02**: Curator can request suggestions from the suggestion API, review returned candidates, and mark each candidate as accepted or rejected in browser memory.
- [x] **CUR-03**: Curator can export accepted in-session candidates as `accepted_candidates.tsv`; the static site does not write back to authoritative SSSOM files or imply automatic write-back.

### Unified Space Packaging

- [x] **SPACE-01**: Maintainer can build a unified Vite+FastAPI Hugging Face Space image: a top-level `server/` FastAPI app (`/health`, `/suggest`, `/convert`) serving the built Vite explorer via `StaticFiles`, packaged by a multi-stage Dockerfile, without importing from `claude_suggestions/` at runtime. (Re-scoped 2026-08-17 from the original Streamlit-scaffold wording after the Streamlit Space packaging approach was reverted in favor of a unified Vite+FastAPI app — see `.planning/phases/05-streamlit-space-packaging/05-CONTEXT.md` D-01.)
- [x] **SPACE-02**: Maintainer can configure the unified Space using documented environment variables/secrets (Blablador, SurrealDB, `SUGGEST_API_ALLOWED_ORIGINS`) instead of hardcoded localhost addresses or local file paths.

### Integration Governance

- [x] **GOV-01**: Integration reuses existing code where scaffolds overlap with repository functionality, avoids duplicate parallel implementations, asks before ambiguous/destructive decisions, and leaves no final imports or runtime references to `claude_suggestions/`.

## v2.1 Requirements

Requirements for the Unified Explorer milestone. Each requirement maps to exactly one roadmap phase.

### Graph Page

- [x] **GRAPH-01**: User can open the unified explorer graph page at `/graph` showing the standards/crosswalks graph built with Cytoscape.js, reusing the same data and behavior (including fullscreen mode) as the existing GitLab Pages explorer.
- [x] **GRAPH-02**: The /graph route loads Cytoscape graph data from the same static JSON file that GitLab Pages uses (`crosswalk_graph.json`), ensuring consistency across deployments.

### Stats Page

- [ ] **STATS-01**: User can open the unified explorer stats page at `/stats` showing pipeline statistics and plots from the latest exports (`exports/pipeline/latest/`), including run metadata and static images for v1.
- [ ] **STATS-02**: The /stats route displays static images for plots (PNG/JPG) and static tables (CSV/TSV) from `exports/pipeline/latest/`; no live backend rendering required for v1.

### Navigation

- [x] **NAV-01**: The unified explorer has a persistent navigation bar on every page (Mappings, Graph, Stats, Convert) allowing users to switch between routes without losing context.

### Data Consistency

- [x] **DATA-02**: Both /graph and /stats routes consume the same pre-exported static JSON/assets that GitLab Pages uses, avoiding duplicate export steps and ensuring consistency.

### Integration Governance

- [ ] **GOV-02**: The .gitlab-ci.yml still contains exactly one `pages` job after the merge, with no additional CI jobs required for the new routes.

## Future Requirements

Deferred beyond this milestone.

### Automation

- **AUTO-01**: Authoritative accepted mappings can be reviewed and merged through an automated repository workflow.
- **AUTO-02**: Deployed suggestion API URL and GitLab Pages URL can be managed through environment-specific deployment automation.

## Out of Scope

Explicitly excluded from v2.0 to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Automatic write-back to authoritative SSSOM files from the static site | The current milestone requires browser-memory decisions and manual merge only. |
| Replacing the existing Streamlit app with scaffold code | The scaffold is packaging/reference material; existing app code remains authoritative. |
| Maintaining two Blablador client implementations | The existing extraction-pipeline client must be reused. |
| Guessing production API or GitLab Pages URLs | Ambiguous deployment URLs require user confirmation. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATA-01 | Phase 02 | Complete |
| WEB-01 | Phase 02 | Complete |
| WEB-02 | Phase 02 | Complete |
| API-01 | Phase 03 | Complete |
| API-02 | Phase 03 | Complete |
| CUR-01 | Phase 04 | Complete |
| CUR-02 | Phase 04 | Complete |
| CUR-03 | Phase 04 | Complete |
| SPACE-01 | Phase 05 | Complete |
| SPACE-02 | Phase 05 | Complete |
| GOV-01 | Phase 02 | Complete |
| GRAPH-01 | Phase 06 | Planned |
| GRAPH-02 | Phase 06 | Planned |
| STATS-01 | Phase 07 | Pending |
| STATS-02 | Phase 07 | Pending |
| NAV-01 | Phase 06 | Complete |
| DATA-02 | Phase 06 | Complete |
| GOV-02 | Phase 06 | Pending |

**Coverage:**

- v2.0 requirements: 11 total
- Mapped to phases: 11
- Unmapped: 0
- All requirements complete — milestone v2.0 fully covered.

- v2.1 requirements: 8 total
- Mapped to phases: 8
- Completed: 2 (NAV-01, DATA-02)
- Pending: 6 (GRAPH-01/02, STATS-01/02, GOV-02)

---
*Requirements defined: 2026-08-25*
*Last updated: 2026-08-25 — v2.1 requirements added (GRAPH-01/02, STATS-01/02, NAV-01, DATA-02, GOV-02); ROADMAP.md updated to include v2.1 milestone with phases 06-07.*
