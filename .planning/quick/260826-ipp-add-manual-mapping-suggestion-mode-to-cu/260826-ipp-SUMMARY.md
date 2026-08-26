---
phase: 260826-ipp
plan: 01
subsystem: ui
tags: [javascript, css, pytest, curation]
requires: []
provides:
  - Inline suggest-mode chooser for LLM vs manual mapping entry
  - Manual candidate form that reuses the shared candidate render/accept/export path
  - Smoke tests that lock the chooser, form-field, and no-network invariants
affects:
  - web curation UI
  - smoke tests
actuals:
  tokens: 3150
  tasks: 2
  commits: 2
tech-stack:
  added: []
  patterns:
    - Vanilla-JS transient mode chooser and form rows
    - data-field-driven manual candidate capture
key-files:
  created: []
  modified:
    - web/src/main.js
    - web/src/style.css
    - tests/test_curation_ui_smoke.py
key-decisions:
  - Manual entries build the same CandidateRule-shaped object and flow through renderCandidateRows + acceptCandidate unchanged.
  - Chooser/form rows are transient and cleared when suggestion mode is reopened.
patterns-established:
  - Shared candidate-row rendering for both LLM and manual suggestions
  - Static smoke tests as the guardrail for UI string invariants
requirements-completed:
  - QUICK-260826-IPP-01
duration: 15m
completed: 2026-08-26
status: complete
---

# Phase 260826-ipp: Manual Mapping Suggestion Summary

Manual entry is now a first-class alternative to the LLM suggestion path, with the same accept/export pipeline and regression coverage.

## Performance

- **Duration:** 15m
- **Tasks:** 2
- **Commits:** 2

## Accomplishments

- Added a suggest-mode chooser in `web/src/main.js` with Ask LLM / Enter manually / Cancel actions.
- Added inline manual candidate entry that reuses `renderCandidateRows(...)` and the existing TSV export path.
- Added CSS for the chooser and form rows.
- Added four smoke tests to lock the chooser markup, manual form fields, shared render path, and unchanged `curation.js` contract.

## Task Commits

1. **Task 1: End-to-end manual-entry candidate path** - `26be34c` (`feat`)
2. **Task 2: Lock in invariants with smoke-test assertions** - `4f516fd` (`test`)

## Files Created/Modified

- `web/src/main.js` - chooser row, manual form row, shared LLM/manual suggestion handling.
- `web/src/style.css` - scoped styles for chooser/form layout and buttons.
- `tests/test_curation_ui_smoke.py` - four new regression tests.

## Decisions Made

- Manual candidates reuse the existing candidate model and acceptance/export flow; `web/src/curation.js` stayed untouched.
- The manual submit path does not call `postSuggestRequest()` or `fetch()`.

## Deviations from Plan

None - plan executed exactly as specified.

## Issues Encountered

- The filtered pytest gate passed for the four new tests. The known pre-existing failure in `test_curation_uses_env_configurable_endpoint` remains out of scope and was not modified.
- Submodule guard passed before both commits; no staged path fell inside `graph-visualizer`.

## Verification

- Task 1 automated gate: passed (`manual path OK`).
- Task 2 pytest gate: `4 passed, 15 deselected`.
- `web/src/curation.js` was not modified.
