---
phase: 260826-ipp
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - web/src/main.js
  - web/src/style.css
  - tests/test_curation_ui_smoke.py
autonomous: false
requirements:
  - QUICK-260826-IPP-01
user_setup: []

estimate:
  tokens: 45000
  raw_tokens: 25000
  tasks: 2
  confidence: low

must_haves:
  truths:
    - Clicking "Suggest candidate mappings" opens an inline mode chooser with two options — "Ask LLM" and "Enter manually" — no immediate network call is made.
    - Choosing "Ask LLM" runs the existing Blablador flow unchanged (POST to /suggest, render returned candidates as rows).
    - Choosing "Enter manually" reveals an inline form with source_path (prefilled from the row's source field, editable), target_path (text), mapping_type (select of direct/conditional/missing/aggregation), confidence (0.0–1.0 number, default 1.0), evidence (text), notes (text), plus a "Add candidate" submit and a Cancel button.
    - Submitting the manual form renders exactly one candidate-row visually identical to LLM-produced candidate rows (same Source/Target/Type/Confidence/Evidence/Notes layout, same Accept/Reject buttons, same mapping_type/confidence labels).
    - Accepting a manually-entered candidate calls the same curation.acceptCandidate path and appears in the TSV export produced by curation.downloadAcceptedTsv() with the same columns (source_standard, source_field, target_path, mapping_type, confidence, evidence, notes).
    - No new fetch/XHR is issued when submitting the manual form; postSuggestRequest is not invoked on the manual path.
  artifacts:
    - web/src/main.js (extended with mode chooser + manual entry form + submit handler that reuses renderCandidateRows)
    - web/src/style.css (styles for .suggest-mode-row, .manual-form-row, .manual-form input/select layout — reusing existing candidate-row look and feel)
    - tests/test_curation_ui_smoke.py (new assertions guarding mode chooser markup, manual form fields, and the "manual path reuses renderCandidateRows without calling postSuggestRequest" invariant)
  key_links:
    - main.js handleSuggestClick → replaced by mode-chooser render → LLM branch keeps existing postSuggestRequest+renderCandidateRows behavior; manual branch builds a CandidateRule-shaped object and calls the SAME renderCandidateRows(triggerRow, sourceField, [manualCandidate]).
    - Manual candidate object shape MUST match the LLM CandidateRule keys exactly: source_path, target_path, mapping_type, confidence (number), evidence, notes — so acceptCandidate / buildAcceptedTsv work without modification.
    - curation.js is NOT modified — the manual path reuses acceptCandidate / getAcceptedCandidates / buildAcceptedTsv unchanged, guaranteeing TSV parity.
---

<objective>
Add a "manual entry" alternative to the LLM-based candidate suggestion flow in the curation UI, without forking the candidate data model.

Purpose: A curator often already knows the correct mapping and just wants to record it — waiting for (or paying for) an LLM call is unnecessary friction. This lets them type the mapping directly and have it flow through the exact same Accept → labeled row → TSV export path as LLM-produced candidates.

Output:
- Updated `web/src/main.js` with an inline mode chooser ("Ask LLM" / "Enter manually") replacing the direct LLM call on suggest-button click, plus an inline manual-entry form whose submit calls the same `renderCandidateRows(...)` used by the LLM path.
- Minimal CSS additions in `web/src/style.css` for the chooser + form rows (reusing the existing `.candidate-row` visual language).
- Extended `tests/test_curation_ui_smoke.py` assertions that lock in the invariants above (mode chooser present, manual form fields present, manual submit does not call `postSuggestRequest`, candidate rendering shared).
</objective>

<execution_context>
@/home/casas/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/casas/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@AGENTS.md
@web/src/curation.js
@web/src/main.js
@web/index.html
@server/main.py
@tests/test_curation_ui_smoke.py
</context>

<tasks>

<task type="tracer">
  <name>Task 1: End-to-end manual-entry candidate path — one candidate flows through the existing Accept + TSV pipeline</name>
  <files>web/src/main.js, web/src/style.css</files>
  <action>
In `web/src/main.js`, refactor the current `handleSuggestClick(button)` so that clicking a `.suggest-btn` no longer immediately POSTs to `/suggest`. Instead:

1. Insert a mode-chooser row (a single `<tr class="suggest-mode-row">` with `colspan="7"`, inserted with `insertAdjacentElement('afterend', ...)` on the triggerRow, `data-source-field="<sourceField>"`) containing two buttons: `.suggest-mode-llm` labeled "Ask LLM" and `.suggest-mode-manual` labeled "Enter manually", plus a `.suggest-mode-cancel` "Cancel" button. Before inserting, call the existing `removeCandidateRows(triggerRow)` so any previous chooser/candidate/form/error rows for this triggerRow are cleared first. Extend `removeCandidateRows` (or the loop that clears rows) so it also removes rows with class `suggest-mode-row` and `manual-form-row` — otherwise stale chooser/form rows will accumulate.

2. Wire the tbody click delegation (`handleTbodyClick`) to route the three new button classes:
   - `.suggest-mode-llm` → remove the chooser row, then invoke the existing LLM logic (extract the current body of `handleSuggestClick` — the fetch + `renderCandidateRows` on success / error row on failure — into a helper `runLlmSuggest(triggerRow, sourceField, button)` and call it here). Behavior of the LLM branch must be identical to today: same `postSuggestRequest` payload, same `renderCandidateRows` call.
   - `.suggest-mode-manual` → remove the chooser row, then insert a `<tr class="manual-form-row">` (colspan="7", `data-source-field="<sourceField>"`) containing a form with these inputs (each with a `data-field` attribute keyed to the CandidateRule field, so the submit handler can read them generically): `source_path` (text, prefilled with `sourceField`), `target_path` (text), `mapping_type` (`<select>` with options `direct`, `conditional`, `missing`, `aggregation`), `confidence` (number, min=0, max=1, step=0.05, default value=1.0), `evidence` (text), `notes` (text), plus `.manual-form-submit` "Add candidate" and `.manual-form-cancel` "Cancel" buttons.
   - `.suggest-mode-cancel` and `.manual-form-cancel` → remove their containing row.
   - `.manual-form-submit` → read the six inputs by `data-field`, coerce `confidence` with `Number(...)` (fall back to 1.0 if `NaN`), build an object with EXACTLY the CandidateRule keys `{ source_path, target_path, mapping_type, confidence, evidence, notes }` (do not add extra keys — the TSV export in `curation.js` reads exactly these), then remove the manual-form row and call the SAME `renderCandidateRows(triggerRow, sourceField, [manualCandidate])` used by the LLM branch. Do NOT introduce a parallel accept path.

3. Constraints:
   - The manual submit path MUST NOT call `postSuggestRequest` or `fetch` — this is the whole point of manual mode.
   - Do not modify `web/src/curation.js`. The manual candidate object must be shaped so that `acceptCandidate`, `getAcceptedCandidates`, and `buildAcceptedTsv` work without any change. Confirm this by re-reading `web/src/curation.js` before submitting.
   - The suggest button label/behavior when re-clicked stays the same ("Suggest candidate mappings") — clicking it again reopens the chooser (previous chooser/form/candidate rows for that triggerRow are cleared first).
   - Keep everything vanilla-JS, no new dependencies, no build-step changes. Match the existing string-template rendering style in `renderCandidateRows` (including `escapeHtml` for anything user-derived that ends up in innerHTML — though for the form we set input `value` via property assignment after `insertAdjacentHTML` to avoid HTML-escaping of the sourceField default).

In `web/src/style.css`, add minimal styles so the chooser row and the manual-form row visually align with the existing `.candidate-row` treatment: put the form fields in a horizontal wrap layout (`display: flex; gap: 0.5rem; flex-wrap: wrap;` on the container div, `.manual-form label { display: inline-flex; flex-direction: column; font-size: 0.85em; }`), and make the chooser row buttons look like the existing action-cell buttons. Do not restyle existing classes; scope everything to the new class names (`.suggest-mode-row`, `.suggest-mode-row button`, `.manual-form-row`, `.manual-form`, `.manual-form label`, `.manual-form input`, `.manual-form select`).

Verification for this task is functional and manual — see `<verify>` — because the web project has no JS test runner (per `web/package.json`, only `vite dev/build/preview`).
  </action>
  <verify>
    <automated>test -f web/src/main.js &amp;&amp; grep -n 'suggest-mode-manual' web/src/main.js &amp;&amp; grep -n 'manual-form-submit' web/src/main.js &amp;&amp; node -e "const fs=require('fs');const s=fs.readFileSync('web/src/main.js','utf8');const lo=s.indexOf('manual-form-submit');const seg=s.slice(lo, lo+4000);if(!/renderCandidateRows\(/.test(seg)){console.error('manual submit path does not reuse renderCandidateRows');process.exit(1)}if(/postSuggestRequest\(/.test(seg)||/fetch\(/.test(seg)){console.error('manual submit path must not call the LLM endpoint');process.exit(1)}console.log('manual path OK')"</automated>
    <human-check>Run `uv run --with fastapi --with uvicorn --with requests uvicorn server.main:app --reload` in one terminal, `npm --prefix web run dev` in another (or `npm --prefix web run build &amp;&amp; npm --prefix web run preview`), open the Explore page in the browser, select any crosswalk row with a Suggest button, click it, choose "Enter manually", fill in a target_path and mapping_type=direct (leave confidence default 1.0), click "Add candidate", verify a candidate row appears with the same look as LLM candidates (mapping_type badge + confidence). Click Accept, verify the "Export accepted" button count increments, click it, and confirm the downloaded TSV contains the manually-entered row with the correct columns.</human-check>
  </verify>
  <done>
Clicking a Suggest button opens an inline mode chooser; picking "Ask LLM" runs the existing flow unchanged; picking "Enter manually" opens an inline form; submitting the form renders a candidate-row visually identical to an LLM one; accepting it increments the export counter and includes it in the downloaded TSV with the correct columns; no network request is made on the manual path.
  </done>
</task>

<task type="auto">
  <name>Task 2: Lock in invariants with smoke-test assertions</name>
  <files>tests/test_curation_ui_smoke.py</files>
  <action>
Append (do NOT rewrite the file) new pytest functions to `tests/test_curation_ui_smoke.py` that assert the manual-entry wiring stays intact. These are static text-grep assertions in the same style as the existing tests in that file (which read `web/src/main.js`, `web/src/curation.js`, `web/index.html`).

Add these tests (function names must be new, do not collide with existing ones):

1. `test_main_js_has_suggest_mode_chooser` — asserts `web/src/main.js` contains the strings `suggest-mode-row`, `suggest-mode-llm`, `suggest-mode-manual` (proves the mode chooser exists and both branches are wired). Use one assert per string with a message identifying the missing token.

2. `test_main_js_has_manual_form_fields` — asserts `web/src/main.js` contains `manual-form-row`, `manual-form-submit`, and each of the six CandidateRule field keys as `data-field="source_path"`, `data-field="target_path"`, `data-field="mapping_type"`, `data-field="confidence"`, `data-field="evidence"`, `data-field="notes"` (proves the manual form exposes exactly the CandidateRule shape).

3. `test_manual_submit_reuses_llm_render_path_without_network` — read `web/src/main.js` once, locate the substring starting at the first occurrence of `manual-form-submit` and ending 4000 chars later (mirroring the Task 1 automated check but in Python), and assert:
   - `'renderCandidateRows('` appears in that slice (manual path reuses the shared renderer),
   - `'postSuggestRequest('` does NOT appear in that slice,
   - `'fetch('` does NOT appear in that slice.
   These three sub-asserts collectively enforce "manual path reuses the LLM render pipeline and issues no network call".

4. `test_curation_js_unchanged_manual_mode_reuses_shared_accept_path` — assert that `web/src/curation.js` still exports exactly the same seven functions listed in the existing `test_curation_module_exists_with_expected_exports` (re-check `export function acceptCandidate`, `export function buildAcceptedTsv`, `export function downloadAcceptedTsv` are present) AND that `web/src/curation.js` does NOT contain a new `manual` branch (grep for `manual` — must be absent). This locks the "curation.js must not fork the model" rule.

Style rules: match the existing test file's style — `from pathlib import Path`, `.read_text(encoding='utf-8')`, plain `assert token in text, f'missing: {token}'`. Do not import pytest fixtures; these are standalone module-level `test_*` functions like the rest of the file.

Do not touch the existing test bodies. If the pre-existing `test_curation_uses_env_configurable_endpoint` test fails (it asserts `http://localhost:8000/suggest` which is not currently in `curation.js`), that failure is pre-existing and out of scope for this task — do NOT modify it.
  </action>
  <verify>
    <automated>uv run --with pytest pytest tests/test_curation_ui_smoke.py -k "manual or suggest_mode_chooser or curation_js_unchanged_manual" -x</automated>
  </verify>
  <done>
The four new tests exist in `tests/test_curation_ui_smoke.py` and pass. They fail-loud if a future edit removes the mode chooser, changes the manual form field keys, makes the manual submit path bypass `renderCandidateRows`, adds a network call to the manual submit path, or forks the manual candidate model into `curation.js`.
  </done>
</task>

</tasks>

<verification>
1. Static gates: `grep -n 'suggest-mode-manual\|manual-form-submit\|renderCandidateRows' web/src/main.js` returns matches; `grep -n 'manual' web/src/curation.js` returns no matches (curation.js unchanged).
2. Test gate: `uv run --with pytest pytest tests/test_curation_ui_smoke.py -k "manual or suggest_mode_chooser or curation_js_unchanged_manual"` passes.
3. Human functional check: manual-entry flow described in Task 1 `<human-check>` produces an accepted row and a TSV containing it, with no network request made when the manual form is submitted (verify in browser DevTools Network tab that no `/suggest` request fires on the manual submit).
</verification>

<success_criteria>
- User can pick between LLM and manual entry after clicking "Suggest candidate mappings".
- Manual candidates render, accept, badge (mapping_type + confidence), and TSV-export identically to LLM candidates.
- `web/src/curation.js` is untouched — the manual path reuses `acceptCandidate` / `buildAcceptedTsv` verbatim.
- No new network call is issued on the manual submit path.
- New smoke tests pass and guard the invariants above.
</success_criteria>

<output>
Create `.planning/quick/260826-ipp-add-manual-mapping-suggestion-mode-to-cu/260826-ipp-SUMMARY.md` when done, summarizing what was changed in `web/src/main.js` (new mode-chooser + manual form + shared render path), the CSS additions, and the four new smoke tests.
</output>
