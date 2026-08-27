---
phase: 260827-gnm
plan: 01
subsystem: web-crosswalk-explorer
tags:
  - crosswalk-labels
  - heading
  - smoke-tests
dependency_graph:
  requires:
    - web/data/crosswalk_graph.json
  provides:
    - compact crosswalk dropdown labels
    - selected crosswalk heading
  affects:
    - web/src/main.js
    - web/index.html
    - web/src/style.css
    - tests/test_curation_ui_smoke.py
tech-stack:
  added:
    - none
  patterns:
    - vanilla JS DOM rendering
    - vanilla CSS
    - pytest smoke coverage
key-files:
  created:
    - .planning/quick/260827-gnm-use-concise-acronym-only-crosswalk-label/260827-gnm-SUMMARY.md
  modified:
    - web/src/main.js
    - web/index.html
    - web/src/style.css
    - tests/test_curation_ui_smoke.py
decisions:
  - Move the expanded crosswalk name into a dedicated heading and keep the dropdown scan-friendly.
  - Preserve natural sorting and the existing curation/export flows unchanged.
metrics:
  duration: PT0H20M
  completed_date: '2026-08-27'
status: complete
---

# Phase 260827-gnm Plan 01 Summary

Compact crosswalk dropdown labels with a live heading for the selected crosswalk.

## What changed

- `web/src/main.js`
  - renders compact `SRC → TGT` dropdown labels derived from crosswalk IDs
  - appends the RDAMSC code only when the ID is non-trivial
  - updates `#current-crosswalk-title` from `display_name` on every selection
- `web/index.html`
  - adds the `current-crosswalk-title` heading above the rules table
- `web/src/style.css`
  - adds a lightweight heading style consistent with the existing UI
- `tests/test_curation_ui_smoke.py`
  - adds ordering and wiring checks for the heading
  - adds compact-label smoke coverage

## Verification

- `uv run --with pytest pytest tests/test_curation_ui_smoke.py tests/test_export_crosswalk_json.py -x` — passed
- `uv run --with ruff ruff check tests/test_curation_ui_smoke.py` — passed

## Deviations from Plan

None - plan executed as written.

## Self-Check: PASSED

- Summary file written
- Commit `27214db` verified in git log
- Focused tests passed
