---
phase: 03-suggestion-api-integration
plan: 02
subsystem: api
tags: [fastapi, blablador, llm-runtime, pytest, cors]

# Dependency graph
requires:
  - phase: 02-static-frontend-data-export
    provides: static explorer context and the /suggest consumer surface
provides:
  - suggestion API wired to shared Blablador runtime config
  - env-driven CORS allowlist for deployment-time origin selection
  - mocked-LLM coverage for happy path, missing key, parse failure, and upstream failure
affects: [phase 04 browser curation workflow]

# Actuals (#2632)
actuals:
  tokens: 4200
  tasks: 3
  commits: 2

# Tech tracking
tech-stack:
  added: [httpx2 for TestClient runtime support]
  patterns: [shared LLM runtime config, env-driven CORS, request-guarded endpoint errors, system-plus-user LLM prompting]

key-files:
  created: [tests/test_suggest_api.py, .planning/phases/03-suggestion-api-integration/03-02-SUMMARY.md]
  modified: [claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/main.py, claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/README.md, .planning/STATE.md, .planning/ROADMAP.md]

key-decisions:
  - "D-05: use SUGGEST_API_ALLOWED_ORIGINS from env, fallback to localhost"
  - "D-06: use pipeline-shaped system + user JSON prompt with temperature=0"
  - "D-07: surface upstream request failures as HTTP 502 and parse failures as HTTP 502"

patterns-established:
  - "Pattern 1: read runtime config via load_llm_runtime_config() instead of module-level env constants"
  - "Pattern 2: keep /suggest response parsing isolated behind parse_candidates()"

requirements-completed: [API-01, API-02]

coverage:
  - id: D1
    description: "Suggestion API stays wired end-to-end for /health and mocked /suggest happy path"
    requirement: API-01
    verification:
      - kind: unit
        ref: "tests/test_suggest_api.py::test_health_ok"
        status: pass
      - kind: unit
        ref: "tests/test_suggest_api.py::test_suggest_happy_path_with_mocked_llm"
        status: pass
    human_judgment: false
  - id: D2
    description: "Suggestion API surfaces D-07 errors and runtime defaults correctly"
    requirement: API-02
    verification:
      - kind: unit
        ref: "tests/test_suggest_api.py::test_suggest_returns_500_when_api_key_missing"
        status: pass
      - kind: unit
        ref: "tests/test_suggest_api.py::test_suggest_returns_502_on_non_json_llm_response"
        status: pass
      - kind: unit
        ref: "tests/test_suggest_api.py::test_suggest_returns_502_on_upstream_network_error"
        status: pass
      - kind: unit
        ref: "tests/test_suggest_api.py::test_defaults_come_from_load_llm_runtime_config"
        status: pass
    human_judgment: false

# Metrics
duration: 35m
completed: 2026-08-16
status: complete
---

# Phase 03: Suggestion API Integration Summary

Shared the suggestion API scaffold with the pipeline's Blablador runtime config, then closed the decision gates and error coverage with mocked FastAPI tests.

## Performance

- **Duration:** 35m
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Rewired `/suggest` to use `load_llm_runtime_config()` and the shared Blablador chat URL helper.
- Switched prompt shape to the pipeline-style system + user JSON contract at `temperature=0`.
- Added env-driven CORS origins, D-07 request-guarded 502 handling, and six passing tests.

## Task Commits

1. **Task 1: End-to-end wiring — one path, one mocked test** - `35d8b80` (feat)
2. **Task 2: Apply D-05 / D-06 choices and harden D-07 errors** - `493b586` (feat)
3. **Task 3: Mocked-LLM tests for D-07 error branches (API-02 completion)** - `a90d46b` (test)

## Files Created/Modified

- `claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/main.py` - shared runtime config, env-driven origins, prompt shape, 502 guard
- `claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/README.md` - canonical env vars and deployment guidance
- `tests/test_suggest_api.py` - mocked FastAPI coverage for happy path, 500, 502 x2, and defaults
- `.planning/STATE.md` - execution state update
- `.planning/ROADMAP.md` - phase progress update

## Decisions Made

- D-05 resolved to env-driven origins with localhost fallback.
- D-06 resolved to pipeline-style system + user prompt shape with `temperature=0`.
- D-07 hardened to convert upstream request failures into HTTP 502 while preserving JSON parse 502 behavior.

## Deviations from Plan

None - plan executed as specified after the user supplied the required D-05 / D-06 decisions.

## Issues Encountered

- Starlette's `TestClient` required `httpx2`; the verification command was rerun with that runtime dependency and then passed.

## Next Phase Readiness

- Phase 03 API integration is complete and verified.
- Phase 04 can consume the stable `/suggest` contract and the documented CORS configuration.

## Self-Check: PASSED

- Summary file exists.
- Task commits exist: 35d8b80, 493b586, a90d46b.

---
*Phase: 03-suggestion-api-integration*
*Completed: 2026-08-16*
