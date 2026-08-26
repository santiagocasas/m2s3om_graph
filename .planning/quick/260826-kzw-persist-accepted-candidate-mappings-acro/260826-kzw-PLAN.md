---
phase: 260826-kzw
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - web/src/main.js
  - web/src/curation.js
  - web/index.html
autonomous: true
requirements:
  - QUICK-260826-kzw

estimate:
  tokens: 18000
  raw_tokens: 12000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - Accepted candidate rows remain visible after user clicks Accept.
    - Accepted candidate rows survive subsequent Suggest / re-suggest actions for the same source field (they are NOT removed when new candidates render).
    - Accepted rows survive re-rendering of the crosswalk (e.g. switching crosswalks then back — restored from `curation.getAcceptedCandidates()`).
    - A per-crosswalk "Export SSSOM" button exists next to the existing "Export accepted (N) as TSV" button.
    - Clicking "Export SSSOM" downloads a valid SSSOM TSV file scoped to the currently selected crosswalk only.
    - SSSOM TSV contains the SSSOM minimal columns: `subject_id`, `predicate_id`, `object_id`, `mapping_justification`, `confidence`, `subject_label`, `object_label`, `comment`.
    - Existing "Export accepted (N) as TSV" behavior is unchanged (still all crosswalks, generic columns).
  artifacts:
    - web/src/curation.js (new exports: `buildSssomTsv(crosswalkId)`, `downloadSssomTsv(crosswalkId)`)
    - web/src/main.js (updated `removeCandidateRows` to skip accepted, updated `renderRules` to restore accepted rows, wired new export button)
    - web/index.html (new `#export-sssom-btn` inside `#controls`)
  key_links:
    - `removeCandidateRows(triggerRow)` in main.js — must preserve rows with class `accepted`.
    - `renderRules(rules)` in main.js — must re-inject accepted candidate rows after each source-field row when rendering a crosswalk.
    - `renderCandidateRows(triggerRow, sourceField, candidates)` — must NOT strip pre-existing accepted rows; and if a new suggested candidate has the same `target_path` as an already-accepted one, dedupe (do not render a duplicate).
    - New SSSOM export button in `#controls` must be enabled/disabled based on `curation.getAcceptedCandidates().filter(e => e.crosswalkId === currentCrosswalkRecord.id).length`.
---

<objective>
Persist accepted candidate mapping rows in the DOM across re-suggest cycles and crosswalk switches, and add a client-side per-crosswalk SSSOM TSV export alongside the existing generic TSV export.

Purpose: Today, accepting a candidate stores the decision in `curation.decisions` but the visual row is wiped the next time the user clicks "Suggest candidate mappings" for the same source field (because `removeCandidateRows` blindly deletes every `.candidate-row` sibling). Users lose visual confirmation of their curation work and cannot see, per source field, what has already been mapped. This task keeps accepted rows visible and adds a proper SSSOM-shaped export scoped to a single crosswalk so users can drop the file straight into SSSOM tooling.

Output:
- Updated `web/src/main.js` with row-preservation and restore-on-render logic.
- Updated `web/src/curation.js` with `buildSssomTsv(crosswalkId)` and `downloadSssomTsv(crosswalkId)`.
- Updated `web/index.html` with a second export button.
- No new dependencies, no backend changes, no changes to `curation.decisions` data model.
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
</context>

<tasks>

<task type="tracer">
  <name>Task 1: Preserve accepted candidate rows across re-suggest for the same source field</name>
  <files>web/src/main.js</files>
  <action>
    Modify `removeCandidateRows(triggerRow)` in `web/src/main.js` so it walks the sibling rows exactly as today (stopping on the first row that is not `.candidate-row`, `.candidate-error`, `.suggest-mode-row`, or `.manual-form-row`) but SKIPS removal for any row that has the `accepted` class — advance to the next sibling instead of removing it. Also update the `candidateRows` WeakMap bookkeeping so that after removal it retains only the accepted rows that survived (do not `candidateRows.delete(triggerRow)` unconditionally; instead set it to the filtered list of surviving accepted rows, or delete only when zero remain). In `renderCandidateRows(triggerRow, sourceField, candidates)`, before inserting new candidate rows, collect any surviving accepted rows for this `sourceField` (from `candidateRows.get(triggerRow)` after the new `removeCandidateRows` runs) and, when iterating the new candidate list, skip any candidate whose `target_path` matches an already-accepted candidate's `target_path` for the same `(crosswalkId, sourceField)` (query via `curation.getDecision(currentCrosswalkRecord.id, sourceField, candidate)` — if it returns `{ status: 'accepted' }`, do not render a duplicate). Keep insertion order: accepted rows stay directly under the trigger row, new suggestion rows are inserted after them using `insertAdjacentElement('afterend', ...)` on the last surviving accepted row (or on `triggerRow` if none). Do NOT modify `curation.js` in this task. Do NOT touch `markCandidateRow` — it already adds the `accepted` class which is now the preservation signal. Verify manually first by running the app and clicking Suggest → Accept → Suggest again on the same source field: the accepted row must remain visible after the second Suggest completes.
  </action>
  <verify>
    <automated>cd web &amp;&amp; npx --yes vite build 2>&amp;1 | tail -20</automated>
  </verify>
  <done>
    `removeCandidateRows` no longer deletes rows with the `accepted` class. `renderCandidateRows` no longer produces duplicate rows for candidates whose `target_path` is already accepted for that source field. `vite build` succeeds with no new errors. Manual smoke: Accept a candidate, click Suggest again on the same source field → the accepted row is still present and the newly suggested rows appear below it, with no duplicate of the accepted target_path.
  </done>
</task>

<task type="auto">
  <name>Task 2: Restore accepted rows when a crosswalk is (re-)rendered</name>
  <files>web/src/main.js</files>
  <action>
    Extend `renderRules(rules)` in `web/src/main.js` so that after the standard row loop populates `tbody`, it iterates over `curation.getAcceptedCandidates()` filtered by `entry.crosswalkId === currentCrosswalkRecord?.id`, and for each accepted entry finds the matching trigger row (the row whose `.suggest-btn` has `data-source-field === entry.sourceField`, matched via a `tbody.querySelector('.suggest-btn[data-source-field="..."]').closest('tr')` lookup; use `CSS.escape` on the source field value). For each match, synthesize a candidate row by extracting the existing rendering logic from `renderCandidateRows` into a small internal helper `createCandidateRowElement(sourceField, candidate, index)` (index can be `0` for restored rows) and inserting it via `insertAdjacentElement('afterend', ...)` immediately after the trigger row, then immediately call `markCandidateRow(row, 'accepted', 'Accepted ✓')` on it so it renders in the disabled accepted state. Also store the candidate in `candidateData` and append the row to `candidateRows.get(triggerRow) || []` so later interactions keep working. Guard against the case where the source field has no `.suggest-btn` (already-mapped rules do not render a Suggest button — skip silently and `console.debug` for diagnostics). Do NOT change the existing rule row rendering. Do NOT persist to localStorage — session-only persistence via the in-memory `decisions` Map is the intended scope. When the user switches crosswalks via the dropdown, `showCrosswalk` already calls `renderRules`, so this restore path runs automatically on switch-back within the same session.
  </action>
  <verify>
    <automated>cd web &amp;&amp; npx --yes vite build 2>&amp;1 | tail -20</automated>
  </verify>
  <done>
    Switching from crosswalk A (with an accepted candidate) to crosswalk B and back to A renders the accepted row under its trigger row in disabled `accepted` state, with buttons showing "Accepted ✓". `vite build` succeeds with no new errors.
  </done>
</task>

<task type="auto">
  <name>Task 3: Add per-crosswalk SSSOM TSV export (button + builder + wiring)</name>
  <files>web/src/curation.js, web/index.html, web/src/main.js</files>
  <action>
    In `web/src/curation.js`, add two new exported functions. `buildSssomTsv(crosswalkId)` returns a string with the SSSOM minimal header `subject_id\tpredicate_id\tobject_id\tmapping_justification\tconfidence\tsubject_label\tobject_label\tcomment\n` followed by one row per entry in `getAcceptedCandidates()` whose `crosswalkId === crosswalkId`. Column mapping per row (all fields must be passed through `sanitizeTsvField`): `subject_id` = `${parseCrosswalkId(entry.crosswalkId)}:${entry.sourceField}`; `predicate_id` = `skos:exactMatch` when `candidate.mapping_type === 'direct'`, `skos:closeMatch` when `candidate.mapping_type === 'conditional'`, `skos:relatedMatch` when `candidate.mapping_type === 'aggregation'`, `sssom:noMapping` when `candidate.mapping_type === 'missing'`, otherwise `skos:relatedMatch`; `object_id` = the target standard (parse from `crosswalkId` by splitting on `_to_` and taking the second segment; add a small helper `parseTargetStandard(crosswalkId)` mirroring `parseCrosswalkId`) concatenated with `:${candidate.target_path}` (or empty string if `target_path` is falsy); `mapping_justification` = `semapv:ManualMappingCuration`; `confidence` = the numeric `candidate.confidence` as-is (or empty if not a number); `subject_label` = `entry.sourceField`; `object_label` = `candidate.target_path ?? ''`; `comment` = `candidate.evidence` concatenated with ` — ${candidate.notes}` when notes is present. `downloadSssomTsv(crosswalkId, filenameOverride)` mirrors the existing `downloadAcceptedTsv` blob/link pattern with content type `text/tab-separated-values;charset=utf-8` and default filename `sssom_${parseCrosswalkId(crosswalkId)}_to_${parseTargetStandard(crosswalkId)}.tsv`. Export `parseTargetStandard` if useful, otherwise keep internal. Do NOT change existing `buildAcceptedTsv` / `downloadAcceptedTsv` — they remain the "all crosswalks generic TSV" export.
    
    In `web/index.html`, inside `<section id="controls">`, insert a new button immediately after `#export-tsv-btn`: `<button id="export-sssom-btn" type="button" disabled>Export SSSOM (0)</button>`.
    
    In `web/src/main.js`: (a) add a module-level `const exportSssomBtn = document.getElementById('export-sssom-btn');` near the existing `exportBtn` declaration; (b) extend `updateExportButton()` to also update `exportSssomBtn` — count = `curation.getAcceptedCandidates().filter(e => e.crosswalkId === currentCrosswalkRecord?.id).length`; set `exportSssomBtn.textContent = \`Export SSSOM (${count})\`;` and `exportSssomBtn.disabled = count === 0 || !currentCrosswalkRecord;`; (c) in `main()` after the existing `exportBtn` click handler, register `exportSssomBtn.addEventListener('click', () =&gt; { if (!exportSssomBtn.disabled &amp;&amp; currentCrosswalkRecord) curation.downloadSssomTsv(currentCrosswalkRecord.id); });`; (d) call `updateExportButton()` at the end of `showCrosswalk` and at the end of `renderRules` (after the accepted-row restore from Task 2) so the SSSOM button state refreshes when switching crosswalks. Handler must guard against `exportSssomBtn` not being an `HTMLButtonElement` just like the existing `exportBtn` guard.
  </action>
  <verify>
    <automated>cd web &amp;&amp; npx --yes vite build 2>&amp;1 | tail -20</automated>
  </verify>
  <done>
    `#export-sssom-btn` renders in the header controls. When a crosswalk with accepted candidates is selected, the button label shows the correct count and is enabled. Clicking it downloads a TSV whose first line is exactly `subject_id\tpredicate_id\tobject_id\tmapping_justification\tconfidence\tsubject_label\tobject_label\tcomment` and whose data rows only include accepted candidates from the currently-selected crosswalk. Switching to a crosswalk with zero accepted candidates disables the button and updates the count to `(0)`. The pre-existing `#export-tsv-btn` behavior is unchanged. `vite build` succeeds.
  </done>
</task>

</tasks>

<verification>
Manual browser smoke test (quick task — no automated e2e infra):
1. `cd web &amp;&amp; npx --yes vite` and open the printed URL.
2. Select any crosswalk with `Suggest candidate mappings` buttons available.
3. Click Suggest on a source field → choose LLM or Manual → Accept one candidate. Row shows "Accepted ✓" in disabled state. `#export-tsv-btn` count increments; `#export-sssom-btn` count increments.
4. Click Suggest on the SAME source field again → new candidates appear BELOW the accepted row; the accepted row is still visible.
5. If the new suggestion list contains the same `target_path` as the accepted one, that duplicate is NOT rendered again.
6. Switch to another crosswalk, then switch back → the accepted row is re-rendered under its trigger row.
7. Click `Export SSSOM (N)` → a `.tsv` downloads. Open it: header matches SSSOM minimal columns, data rows only correspond to the currently-selected crosswalk.
8. Click the existing `Export accepted (N) as TSV` button → unchanged generic TSV downloads (all crosswalks).
</verification>

<success_criteria>
- Accepted rows survive re-suggest on the same source field.
- Accepted rows are restored when the user leaves and returns to a crosswalk within the same session.
- `#export-sssom-btn` exists, counts accepted candidates for the current crosswalk, and downloads a valid SSSOM-shaped TSV scoped to that crosswalk.
- No changes to `curation.decisions` data model; no backend changes; no new dependencies; `vite build` succeeds.
</success_criteria>

<output>
Create `.planning/quick/260826-kzw-persist-accepted-candidate-mappings-acro/260826-kzw-01-SUMMARY.md` when done.
</output>
