---
phase: 260827-g0f
plan: 01
subsystem: web-crosswalk-explorer
tags:
  - crosswalk-labels
  - natural-sort
  - sssom-export
dependency_graph:
  requires:
    - exports/sssom/*.sssom.tsv
    - web/data/crosswalk_graph.json
  provides:
    - human-readable crosswalk dropdown labels
    - natural ordering for rdamsc crosswalk IDs
    - regenerated crosswalk_graph.json with display_name fields
  affects:
    - scripts/export_crosswalk_json.py
    - web/src/main.js
    - tests/test_export_crosswalk_json.py
    - tests/test_curation_ui_smoke.py
    - web/data/crosswalk_graph.json
tech-stack:
  added:
    - none
  patterns:
    - Python stdlib export pipeline
    - vanilla JS DOM rendering
    - pytest coverage
    - Ruff linting
key-files:
  created:
    - .planning/quick/260827-g0f-show-each-rdamsc-crosswalk-s-human-reada/260827-g0f-SUMMARY.md
  modified:
    - scripts/export_crosswalk_json.py
    - web/src/main.js
    - tests/test_export_crosswalk_json.py
    - tests/test_curation_ui_smoke.py
    - web/data/crosswalk_graph.json
decisions:
  - Keep DataCite 4.4 → DCTerms grounded in committed SSSOM/JSON evidence; do not fabricate a catalog record.
  - Mirror the authoritative export into both web/public/data and web/data so the browser path and committed fixture stay aligned.
  - Use display_name first, then standards-name fallback, then raw IDs; apply natural sorting in export and frontend.
metrics:
  duration: PT0H35M
  completed_date: '2026-08-27'
status: complete
actuals:
  tokens: 230000
  tasks: 3
  commits: 3
---

# Phase 260827-g0f Plan 01 Summary

Human-readable crosswalk labels with natural rdamsc ordering, backed by committed SSSOM provenance.

## DataCite 4.4 → DCTerms provenance

- SSSOM source: `exports/sssom/datacite44_to_dcterms.sssom.tsv`
- Header evidence:
  - `#mapping_set_id: m2s3om_graph:datacite44_to_dcterms`
  - `#mapping_set_description: DataCite 4.4 to Dublin Core Terms (DataCite -> Dublin Core Terms)`
  - `#mapping_set_source: file:///home/casas/AI/Metadata-Mappings/DataCite_DublinCore_Mapping.pdf`
- Row count: 110 mapping rows
- Regenerated JSON evidence: `web/data/crosswalk_graph.json`
  - `id`: `datacite44_to_dcterms`
  - `source`: `datacite44`
  - `target`: `dcterms`
  - rule count: 110
- Standards lookup:
  - `datacite44` → `DataCite`
  - `dcterms` → `Dublin Core Terms`

Conclusion: the crosswalk was present all along; the user-visible problem was the label shape, not missing data.

## What changed

- `scripts/export_crosswalk_json.py`
  - emits `display_name` for every crosswalk
  - strips trailing parentheticals from SSSOM descriptions
  - natural-sorts crosswalk IDs
  - mirrors the generated JSON into `web/data/crosswalk_graph.json`
- `web/src/main.js`
  - renders `display_name` first
  - falls back to standards names with `→`
  - keeps raw IDs as a last resort
  - applies defensive natural sorting before populating the select
- Tests:
  - `tests/test_export_crosswalk_json.py`
  - `tests/test_curation_ui_smoke.py`

## Verification

- `uv run --with pytest pytest tests/test_export_crosswalk_json.py tests/test_curation_ui_smoke.py tests/test_vite_smoke.py -x`
  - passed
- `uv run --with ruff ruff check scripts/export_crosswalk_json.py tests/test_export_crosswalk_json.py tests/test_curation_ui_smoke.py`
  - passed

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated curation endpoint expectation in smoke test**
- **Found during:** verification
- **Issue:** the test expected a hardcoded localhost suggest URL that is not present in `web/src/curation.js`
- **Fix:** aligned the assertion with the actual `/suggest` default
- **Files modified:** `tests/test_curation_ui_smoke.py`
- **Commit:** `c57c7c7`

## Known Limitations

- RDAMSC crosswalk descriptions can still be sparse, so some human-readable labels remain thin (for example `rdamsc_c11`-style rows). That is a data-ingest follow-up, not a rendering bug.

## Self-Check: PASSED

- Summary file written
- Commit hashes verified in git log
- Verification commands passed
