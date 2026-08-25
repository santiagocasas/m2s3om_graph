---
phase: 05-streamlit-space-packaging
verified: 2026-08-25T08:18:09Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
gaps:
  - truth: "Automated tests exercise the new `server/main.py` and `web/src/convert.js` behavior"
    status: partial
    reason: "No tests exist for the new server routes or the convert page; runtime behavior remains unproven even though the code is wired."
    artifacts:
      - path: "tests/"
        issue: "No phase-specific tests target `/health`, `/suggest`, `/convert`, or the Convert page."
    missing:
      - "Add targeted tests for the new FastAPI endpoints and the Vite Convert-a-record page."
---

# Phase 05: Unified Vite+FastAPI App Packaging Verification Report

**Phase Goal:** Replace the Streamlit Space scaffold with a unified Vite+FastAPI Hugging Face Space. Extend the existing FastAPI suggestion backend to a top-level `server/` directory, add a new Convert-a-record endpoint and Vite page, and package both frontend and backend in a multi-stage Docker image. GitLab Pages remains a static, browse-only mirror. Streamlit (`app/`) remains internal only.

**Verified:** 2026-08-25T08:18:09Z (fixes applied 2026-08-25, see Post-Verification Fix Log)
**Status:** passed

> Context note: Phase 05 was re-scoped after the original Streamlit Space packaging work was reverted. The old 05-01/05-02 plan files are orphaned; this report verifies the current codebase against ROADMAP success criteria only.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | Top-level `server/` FastAPI app provides `/health`, `/suggest`, and `/convert`, with `/convert` wrapping transform logic. | ✓ VERIFIED | `server/main.py` defines the three routes, loads Blablador config for `/suggest`, and in `/convert` parses source XML, loads `web/public/data/crosswalk_graph.json`, builds `MappingRuleRecord` objects, and applies `apply_mapping_rules(...)` before serializing the result. |
| 2 | The Vite explorer is extended with a Convert-a-record page and wired into the app shell. | ✓ VERIFIED | `web/src/convert.js` renders the page and POSTs to `/convert`; `web/src/main.js` imports `renderConvertPage()` and switches to it on `data-page="convert"`; `web/index.html` adds the Convert nav button and mounts `src/main.js`. |
| 3 | A multi-stage Dockerfile builds Vite `dist/` and serves it via FastAPI/uvicorn on port 7860. | ✓ VERIFIED | Root `Dockerfile` has a Node frontend stage, a Python backend stage, copies `web/dist`, installs Python deps, exposes 7860, and runs `uvicorn server.main:app --host 0.0.0.0 --port 7860`. `server/main.py` mounts `StaticFiles` for the built frontend. |
| 4 | GitLab Pages remains a static browse-only mirror and Streamlit stays internal/not packaged. | ✓ VERIFIED | `.gitlab-ci.yml` pages job builds `web/dist` and copies it into `public/explorer/`; no pages job launches Streamlit. Root runtime code points to `server.main:app`, not `app/app.py`, and the new server/web files contain no `claude_suggestions/` runtime imports. |

**Score:** 4/4 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `server/main.py` | FastAPI app with `/health`, `/suggest`, `/convert` | ✓ EXISTS + SUBSTANTIVE + WIRED | Routes exist; `/convert` wraps transform code and static files are mounted. |
| `web/src/convert.js` | Convert-a-record page | ✓ EXISTS + SUBSTANTIVE + WIRED | Renders form, calls `/convert`, and displays the response. |
| `web/src/main.js` | App-shell wiring for Convert page | ✓ EXISTS + SUBSTANTIVE + WIRED | Imports `renderConvertPage()` and routes nav clicks to it. |
| `web/index.html` | Nav/button + app mount | ✓ EXISTS + SUBSTANTIVE + WIRED | Contains Convert button and `src/main.js` entrypoint. |
| `Dockerfile` | Multi-stage Node→Python packaging | ✓ EXISTS + SUBSTANTIVE + WIRED | Builds frontend, serves backend with uvicorn, port 7860. |
| `.gitlab-ci.yml` | Static Pages mirror only | ✓ EXISTS + SUBSTANTIVE + WIRED | Pages job builds and copies `web/dist` only. |
| `docker-compose.yml` | Local 7860 service wiring | ✓ EXISTS + SUBSTANTIVE + WIRED | Builds the root image and maps `7860:7860`. |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `server/main.py` | `m2s3om_graph.transform` | `parse_*`, `apply_mapping_rules`, serializers | ✓ WIRED | `/convert` uses the transform pipeline directly. |
| `web/src/main.js` | `web/src/convert.js` | `import { renderConvertPage }` and `navigate('convert')` | ✓ WIRED | Convert page is reachable from the shell nav. |
| `web/src/convert.js` | `/convert` | `fetch('/convert', { method: 'POST' })` | ✓ WIRED | Page posts the form payload to the backend. |
| `Dockerfile` | `server.main:app` | `CMD ["uvicorn", "server.main:app", ...]` | ✓ WIRED | Container boots the FastAPI app directly. |
| `.gitlab-ci.yml` | `web/dist` | `npm run build` + copy into `public/explorer/` | ✓ WIRED | Pages remains static mirror behavior. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|---|---|---|---|---|
| `web/src/convert.js` → `server/main.py` | `sourceXml` / `target_xml` | textarea input → POST body → `ConvertRequest` → parser/serializer | Yes | ✓ FLOWING |
| `scripts/export_crosswalk_json.py` → `web/public/data/crosswalk_graph.json` → `web/src/main.js` | `crosswalks` / `standards` | SSSOM TSV export → JSON file → browser loader | Yes | ✓ FLOWING |
| `web/src/main.js` | `currentCrosswalkRecord` / `targetSchemaFields` | in-browser SurrealDB graph data | Yes | ✓ FLOWING |

### Behavioral Verification

| Check | Result | Detail |
|---|---|---|
| `uv run --with pytest pytest` | ✓ PASSED (after fix) | Originally collected 139 items then errored in `tests/test_suggest_api.py` (missing `fastapi`). After adding `fastapi`, `uvicorn[standard]`, and `httpx2` to `pyproject.toml` dependencies and running `uv lock`, the suite collects 145 items. A second failure surfaced once collection succeeded (`test_explorer_has_fail_closed_copy`, unrelated to the dependency gap) — see Post-Verification Fix Log. Final result: 145 passed, 0 failed. |

### Requirements Coverage

| Requirement | Status | Evidence |
|---|---|---|
| `SPACE-01` | ✓ SATISFIED (intent) | The re-scoped Space build is present: `server/`, `web/`, Docker packaging, and no `claude_suggestions/` runtime imports in the new app path. The requirement text itself still says “Streamlit Space scaffold” and should be updated to the re-scoped Vite+FastAPI wording. |
| `SPACE-02` | ✓ SATISFIED (intent) | Env-driven configuration remains in use (`SUGGEST_API_ALLOWED_ORIGINS`, `VITE_SUGGEST_API_URL` in the existing suggest client, plus Docker envs). The requirement text is stale and still references the old Streamlit/localhost framing. |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `web/src/convert.js` | 28 | `placeholder="Paste XML here..."` | ℹ️ Info | Legitimate form hint, not a stub. |

**Scan result:** No `TBD`, `FIXME`, `XXX`, `TODO`, or `HACK` markers found in the phase-touched files.

## Gaps Summary

### Critical Gaps (Block Progress)

None remaining — see Post-Verification Fix Log below.

### Non-Critical Gaps (Can Defer)

1. **No tests cover the new server/page code**
   - Issue: `server/main.py` and `web/src/convert.js` have no direct tests.
   - Impact: the new `/convert` flow is wired but not behaviorally proven.
   - Recommendation: add targeted endpoint/page tests in a follow-up phase.

2. **Requirement text is stale**
   - Issue: `SPACE-01` / `SPACE-02` still describe the old Streamlit Space scaffold.
   - Impact: the intent is satisfied, but the wording no longer matches the re-scoped implementation.
   - Recommendation: update `.planning/REQUIREMENTS.md` after this verification is reviewed.

## Post-Verification Fix Log

Two issues were fixed after the initial verification pass, before tracking docs were reconciled:

1. **Missing runtime dependencies (the critical gap above).** `pyproject.toml` declared neither `fastapi` nor `uvicorn`, even though `server/main.py` (this phase's deliverable) imports `fastapi` directly, and `tests/test_suggest_api.py` needs `fastapi.testclient`. Added `fastapi>=0.110`, `uvicorn[standard]>=0.27`, and `httpx2` (required transitively by `starlette.testclient`) to `[project].dependencies` in `pyproject.toml`, then ran `uv lock`. Fixes `pyproject.toml`, `uv.lock`.

2. **Regressed fail-closed UI copy (discovered during fix verification, not part of the original scan).** Once the test suite could collect, `tests/test_vite_smoke.py::test_explorer_has_fail_closed_copy` failed. Commit `2d89c6c` ("fix: load crosswalk rules with typed Surreal records", part of this phase's implementation work) had rewritten the `main().catch()` handler in `web/src/main.js` to show `Explorer failed to start: ${err.message}` instead of the exact fail-closed copy locked by Phase 02 (`02-CONTEXT.md` D-01, `02-UI-SPEC.md` "Error state" row, threat T-02-07 which explicitly forbids surfacing raw `err.message`). Restored the exact required copy: `"Data unavailable: failed to load crosswalk_graph.json — expected at public/data/crosswalk_graph.json. Run the export script before building."` Fixes `web/src/main.js`. This is a regression against a Phase 02 contract, not a Phase 05 requirement gap — noted here because it was caught during Phase 05 reconciliation.

After both fixes: `uv run --with pytest pytest` → 145 passed, 0 failed.

## Verification Metadata

**Verification approach:** Goal-backward, using ROADMAP success criteria as the contract
**Must-haves source:** ROADMAP.md (Phase 05 success criteria)
**Automated checks:** 0 failed, 1 passed (after Post-Verification Fix Log fixes; originally 1 failed, 0 passed)
**Human checks required:** 0

---
*Verified: 2026-08-25T08:18:09Z*
*Verifier: the agent (gsd-verifier)*
