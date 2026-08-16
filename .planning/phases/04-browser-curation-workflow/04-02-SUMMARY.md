---
phase: 04-browser-curation-workflow
plan: 02
subsystem: browser-curation-workflow
tags: [browser, curation, tsv, export, notice, smoke-tests]
dependency_graph:
  requires:
    - 04-01
  provides:
    - CUR-03
  affects:
    - web/index.html
    - web/src/main.js
    - web/src/curation.js
    - web/src/style.css
    - tests/test_curation_ui_smoke.py
tech_stack:
  added:
    - Blob-backed TSV download
    - export-button count refresh
    - manual no-write-back notice
    - extended smoke coverage
  patterns:
    - client-side TSV generation
    - object-URL lifecycle cleanup
    - additive UI wiring
key_files:
  modified:
    - web/index.html
    - web/src/main.js
    - web/src/curation.js
    - web/src/style.css
    - tests/test_curation_ui_smoke.py
decisions:
  - Accepted candidates export as `accepted_candidates.tsv` by default.
  - Export stays client-side only; no write-back path is introduced.
  - The UI explicitly states the manual merge boundary.
metrics:
  duration: "~1h"
  completed: "2026-08-16"
status: complete
actuals:
  tokens: 2600
  tasks: 2
  commits: 2
---

# Phase 04 Plan 02: Browser Curation Workflow Summary

Browser curation now includes manual TSV export of accepted candidates plus an explicit notice that the explorer never writes back to authoritative files.

## Completed Tasks

| Task | Name | Commit | Files |
| ---- | ---- | ------ | ----- |
| 1 | TSV export path | `2fad3f0` | `web/index.html`, `web/src/main.js`, `web/src/curation.js`, `web/src/style.css` |
| 2 | Extended smoke tests | `6872335` | `tests/test_curation_ui_smoke.py` |

## Verification

- `uv run --with pytest pytest tests/test_curation_ui_smoke.py -x -v` ✅
- `uv run --with pytest pytest tests/ -x -q` ⚠️ blocked by unrelated `tests/test_suggest_api.py` import error: `ModuleNotFoundError: No module named 'fastapi'`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed the TSV header test literal**
- **Found during:** Task 2
- **Issue:** The raw TSV-header assertion used real tab characters instead of escaped `\t` sequences.
- **Fix:** Updated the smoke test to grep the literal `\t` escape sequence emitted by the JS source.
- **Files modified:** `tests/test_curation_ui_smoke.py`
- **Commit:** `6872335`

## Deferred Issues

- Full-suite verification is blocked by a missing `fastapi` dependency in `tests/test_suggest_api.py`; logged in `.planning/phases/04-browser-curation-workflow/deferred-items.md`.

## Self-Check: PASSED
