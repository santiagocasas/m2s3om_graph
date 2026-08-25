# Phase 02 Discussion Log

**Phase:** 02 Static Frontend Data Export  
**Date:** 2026-08-14  
**Mode:** Interactive discuss-phase

## Session Summary
User requested progress assessment and Phase 02 discussion. Gray areas presented via interactive questions. Decisions captured for Site integration, Data contract, Graph identifiers, and Build orchestration.

## Questions and Answers

### Site integration
**Q:** How should the explorer be exposed inside the unified Pages site?
**A:** Dedicated Explorer page (Recommended)

**Q:** What URL shape should the dedicated explorer use?
**A:** `explorer/` (Recommended)

**Q:** How should visitors reach the explorer from the existing generated site?
**A:** Header nav plus overview card (Recommended)

**Q:** What should the explorer do if the generated JSON is missing, stale, or malformed?
**A:** Visible fail-closed state (Recommended)

**Q:** How closely should the explorer match the existing Pages shell?
**A:** Reuse shell language, separate app styling (Recommended)

### Data contract
**Q:** What should the exported browser JSON contain for each rule?
**A:** Rich audit record (Recommended)

**Q:** How should the browser data label deterministic versus LLM-assisted mappings?
**A:** Explicit `strategy` field (Recommended)

**Q:** What evidence should accompany each exported rule?
**A:** Structured provenance plus source link (Recommended)

**Q:** How should multi-path source and target mappings be represented?
**A:** Arrays plus display labels (Recommended)

**Q:** How should crosswalks with missing or non-mappable rules appear in the export?
**A:** Include explicit missing-rule records (Recommended)

### Graph identifiers
**Q:** How should crosswalk and standard IDs be handled in the browser explorer?
**A:** Preserve and safely encode (Recommended)

**Q:** What should users see when a crosswalk or standard is selected?
**A:** Canonical ID and human label (Recommended)

**Q:** How should browser-local SurrealDB keys be made safe?
**A:** Deterministic encoded key (Recommended)

**Q:** What should happen if two canonical IDs map to the same safe browser key?
**A:** Add a stable hash suffix

**Q:** How should the explorer relate crosswalk IDs to the existing graph visualizations?
**A:** Link by canonical ID (Recommended)

### Build orchestration
**Q:** How should the existing Python Pages generator and Vite build be combined?
**A:** Single Pages job, Python then Vite (Recommended)

**Q:** What should the combined local/CI build sequence be?
**A:** Export, Python site, Vite explorer (Recommended)

**Q:** How should the Pages job obtain Node/Vite dependencies?
**A:** Pinned Node image and lockfile (Recommended)

**Q:** What should make the Pages build fail rather than publish a partial site?
**A:** Warn but publish

**Q:** How should maintainers run the integrated build locally?
**A:** One documented command (Recommended)

## Decisions Locked
- Explorer at `docs/pages/explorer/` with header nav + overview card.
- Rich audit JSON export with strategy, provenance, path arrays, missing rules.
- Canonical IDs displayed, deterministic encoded safe keys with hash suffix on collision.
- Single Pages CI job: export → Python site → Vite build.
- Warn-but-publish failure policy with visible fail-closed UI.

## Artifacts Created
- `.planning/phases/02-static-frontend-data-export/02-CONTEXT.md`

## Next
Proceed to `/gsd-plan-phase 02`.
