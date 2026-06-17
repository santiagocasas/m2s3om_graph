# Requirements: m2s3om_graph v2.0 Deployment Surfaces

**Defined:** 2026-06-17
**Core Value:** Enable cross-walking between metadata standards by providing machine-readable mapping rules that can be applied automatically while tracking semantic loss.

## v2.0 Requirements

Requirements for the Deployment Surfaces milestone. Each requirement maps to exactly one roadmap phase.

### Data Export

- [ ] **DATA-01**: Maintainer can run a Python export script in the existing pipeline codebase that reads committed SSSOM TSV files plus the standards list and writes static-site JSON matching the scaffold README shape: `standards[]`, `crosswalks[]`, and nested `rules[]`.

### Static Frontend

- [ ] **WEB-01**: User can open the GitLab Pages crosswalk explorer built from the integrated Vite scaffold in the repository's canonical Pages source, using the real exported JSON instead of the scaffold sample data.
- [ ] **WEB-02**: Maintainer can run the local static frontend build successfully with `npm install` and `npm run build`, and GitLab CI contains exactly one `pages` job for publishing the site.

### Suggestion API

- [ ] **API-01**: The suggestion API keeps the existing `call_blablador(prompt: str) -> str` signature while delegating to the repository's existing Blablador client and matching its default base URL/model settings.
- [ ] **API-02**: Maintainer can run mocked-LLM tests confirming `/health` and `/suggest` still work after the real Blablador client is wired in.

### Curation UI

- [ ] **CUR-01**: Curator sees a "Suggest candidate mappings" action only for source fields that have no existing rule in the currently selected crosswalk.
- [ ] **CUR-02**: Curator can request suggestions from the suggestion API, review returned candidates, and mark each candidate as accepted or rejected in browser memory.
- [ ] **CUR-03**: Curator can export accepted in-session candidates as `accepted_candidates.tsv`; the static site does not write back to authoritative SSSOM files or imply automatic write-back.

### Streamlit Space

- [ ] **SPACE-01**: Maintainer can build a Hugging Face Space scaffold containing the existing Streamlit app entrypoint, supporting modules, requirements, Dockerfile, and README without importing from `claude_suggestions/`.
- [ ] **SPACE-02**: Maintainer can configure the Streamlit Space using documented environment variables/secrets instead of hardcoded localhost addresses or local file paths, including SurrealDB connection settings.

### Integration Governance

- [ ] **GOV-01**: Integration reuses existing code where scaffolds overlap with repository functionality, avoids duplicate parallel implementations, asks before ambiguous/destructive decisions, and leaves no final imports or runtime references to `claude_suggestions/`.

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
*Requirements defined: 2026-06-17*
*Last updated: 2026-06-17 after roadmap creation*
