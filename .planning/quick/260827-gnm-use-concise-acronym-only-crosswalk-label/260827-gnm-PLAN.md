---
phase: 260827-gnm
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - web/src/main.js
  - web/index.html
  - web/src/style.css
  - tests/test_curation_ui_smoke.py
autonomous: true
requirements:
  - QUICK-260827-GNM
must_haves:
  truths:
    - "The crosswalk dropdown shows compact source→target labels (e.g. `DATACITE44 → DCTERMS (rdamsc_c1)`) without the long human-readable standard names."
    - "The RDAMSC code (the crosswalk `id`, e.g. `rdamsc_c1`) is retained in parentheses at the end of every RDAMSC-derived dropdown option."
    - "A heading above the rules table names the currently selected crosswalk using its `display_name` (the expanded, human-readable form)."
    - "Changing the dropdown selection updates the heading text before the rules render."
    - "Natural sort order and `display_name` provenance introduced by quick task 260827-g0f are preserved."
  artifacts:
    - web/src/main.js
    - web/index.html
    - web/src/style.css
    - tests/test_curation_ui_smoke.py
  key_links:
    - "`populateSelect` in `web/src/main.js` derives compact labels from the crosswalk `source` / `target` / `id` fields, not from the standards `name` map."
    - "`showCrosswalk` in `web/src/main.js` writes the heading text from `record.display_name` on every selection change (including initial load)."
    - "`index.html` exposes a stable element (e.g. `#current-crosswalk-title`) above `#rules-table-container` for the heading."
---

<objective>
Replace the long, human-readable crosswalk dropdown labels with compact source→target identifiers that retain the RDAMSC code, and add a descriptive heading above the rules table that identifies the currently selected crosswalk using its expanded `display_name`.

Purpose: The dropdown got too verbose after 260827-g0f — long standard names like "ABCD (Access to Biological Collection Data) → Darwin Core" crowd the control. The user wants the dropdown to read like a scan-friendly identifier list, while the descriptive expansion moves to a dedicated title above the table where it has room to breathe and can double as an explanation of the currently selected crosswalk.

Output: Updated `web/src/main.js`, `web/index.html`, `web/src/style.css`, and `tests/test_curation_ui_smoke.py` proving the compact dropdown label shape and the dynamically updated table heading.
</objective>

<execution_context>
@/home/casas/.config/opencode/gsd-core/workflows/execute-plan.md
@/home/casas/.config/opencode/gsd-core/templates/summary.md
</execution_context>

<context>
@AGENTS.md
@.planning/STATE.md
@.planning/quick/260827-g0f-show-each-rdamsc-crosswalk-s-human-reada/260827-g0f-SUMMARY.md
@web/index.html
@web/src/main.js
@web/src/style.css
@tests/test_curation_ui_smoke.py
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Compact dropdown label + dynamic table heading (end-to-end)</name>
  <files>web/src/main.js, web/index.html, web/src/style.css</files>
  <behavior>
    - `buildCrosswalkLabel(cw, standardName)` returns a compact label of the shape `SRC → TGT (id)` for RDAMSC crosswalks (e.g. `RDAMSC_C1 → DST_RDAMSC_C1 (rdamsc_c1)`), and `SRC → TGT` for non-RDAMSC crosswalks whose `id` already equals `${source}_to_${target}` (e.g. `DATACITE44 → DCTERMS`) so the code is not duplicated.
    - The compact SRC/TGT tokens are derived from the crosswalk `source` and `target` standard IDs (uppercased, `dst_` prefix stripped) — NOT from the standards `name` map. Long expanded names like "Access to Biological Collection Data" must not appear in any `<option>` text.
    - `display_name` is NO LONGER used to build the `<option>` label — the compact identifier form always wins for the dropdown. `display_name` is still read from the crosswalk record for the heading.
    - The heading element (id `current-crosswalk-title`) lives in `index.html` above `#rules-table-container` and is updated by `showCrosswalk` on every selection change: text is `record.display_name` when present, otherwise the compact dropdown label as a fallback, otherwise empty. Initial load also populates it.
    - Existing natural sort order (`compareNaturalKeys(naturalKey(...))`) and the `→` separator are preserved.
    - All existing behavior in `renderRules`, curation flows, and export buttons is untouched.
  </behavior>
  <action>
    Rewrite `buildCrosswalkLabel` in `web/src/main.js` so the dropdown option text is a compact `SRC → TGT` identifier (uppercased standard IDs, `dst_` prefix stripped) with the crosswalk `id` appended in parentheses ONLY when it is not already the trivial `${source}_to_${target}` form — this keeps `DATACITE44 → DCTERMS` clean and yields `RDAMSC_C1 → DST_RDAMSC_C1 (rdamsc_c1)` for RDAMSC rows so the RDAMSC code is retained. Do NOT read the standards `name` map for label text. Do NOT use `display_name` for the dropdown label (it becomes the heading text instead). Keep the `→` character, `naturalKey`, and `compareNaturalKeys` intact so sort order matches 260827-g0f. In `web/index.html`, add `<h2 id="current-crosswalk-title" class="crosswalk-title"></h2>` immediately above `<section id="rules-table-container">`. Grab that node in `main.js` (`document.getElementById('current-crosswalk-title')`) and update its `textContent` inside `showCrosswalk` on every call: prefer `record.display_name` (trimmed), fall back to the compact dropdown label rebuilt from the current crosswalk + standards map, and clear it when no crosswalk is selected. Ensure the initial `showCrosswalk` call after `populateSelect` populates the heading (this is already covered by the existing initial-load path in `main`). Add a lightweight `.crosswalk-title` style block to `web/src/style.css` matching the existing visual language (use `var(--ink)`, modest top/bottom margin, sensible font-size — no new tokens, no new dependencies, vanilla CSS only).
  </action>
  <verify>
    <automated>uv run --with pytest pytest tests/test_curation_ui_smoke.py -x</automated>
  </verify>
  <done>
    - `web/index.html` contains `id="current-crosswalk-title"` above `#rules-table-container`.
    - `web/src/main.js` `buildCrosswalkLabel` never reads the standards `name` map for dropdown label text and never uses `display_name` for the dropdown; RDAMSC rows include the `(rdamsc_c*)` suffix; `datacite44_to_dcterms` renders as `DATACITE44 → DCTERMS` (no redundant `(datacite44_to_dcterms)`).
    - `showCrosswalk` updates `#current-crosswalk-title.textContent` on every invocation using `display_name` when available.
    - Natural sort behavior of the dropdown is unchanged (existing sort code retained).
    - Existing curation, export, and rendering flows still work — no other functions modified beyond the two named above and the heading wiring.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Smoke coverage for compact labels + dynamic heading</name>
  <files>tests/test_curation_ui_smoke.py</files>
  <behavior>
    - A test asserts `web/index.html` contains `id="current-crosswalk-title"` and that the element sits above `id="rules-table-container"` in source order.
    - A test asserts `web/src/main.js` `buildCrosswalkLabel` no longer reads `standardName.get(cw?.source)` / `standardName.get(cw?.target)` to build the option text (i.e. the old `cleanStandardName(standardName.get(...))` construction is gone) and no longer uses `cw?.display_name` in the returned dropdown string.
    - A test asserts `web/src/main.js` uppercases the source/target standard IDs and strips a leading `dst_` prefix when composing the compact label (e.g. via a `.toUpperCase()` call and `dst_` handling inside or near `buildCrosswalkLabel`).
    - A test asserts `showCrosswalk` in `web/src/main.js` reads `record?.display_name` and writes to `current-crosswalk-title` (or the element it resolves to) on every call — captured by the presence of both `current-crosswalk-title` and `display_name` inside the `showCrosswalk` body region.
    - Existing tests continue to pass (natural sort, display_name provenance in the export pipeline, curation module invariants).
  </behavior>
  <action>
    Extend `tests/test_curation_ui_smoke.py` with focused pytest functions that read `web/index.html` and `web/src/main.js` as text and assert the invariants above. Use string containment and simple ordering checks (`html.index('current-crosswalk-title') < html.index('rules-table-container')`). For the `showCrosswalk` region check, slice `main.js` from `async function showCrosswalk` to the next top-level `function ` / `async function ` and assert both `display_name` and `current-crosswalk-title` appear inside that slice. Keep the existing `test_main_js_populate_select_prefers_display_name_then_standards_fallback` test aligned with reality: since `display_name` is no longer used for the dropdown label, either update that assertion to check that `display_name` is used inside the `showCrosswalk` region (for the heading) and that `naturalKey` + `→` are still present in `main.js`, or split it into two tests — one for dropdown sort/label invariants, one for heading invariants. Do NOT weaken the existing persistence-free and export-button assertions.
  </action>
  <verify>
    <automated>uv run --with pytest pytest tests/test_curation_ui_smoke.py tests/test_export_crosswalk_json.py -x</automated>
  </verify>
  <done>
    - `tests/test_curation_ui_smoke.py` gains at least two new assertions (compact-label shape and dynamic heading wiring) and the pre-existing `display_name`/`naturalKey` test still passes under the new label rules.
    - `uv run --with pytest pytest tests/test_curation_ui_smoke.py tests/test_export_crosswalk_json.py -x` is green.
    - `uv run --with ruff ruff check tests/test_curation_ui_smoke.py` is green.
  </done>
</task>

</tasks>

<verification>
- `uv run --with pytest pytest tests/test_curation_ui_smoke.py tests/test_export_crosswalk_json.py -x` — full green.
- `uv run --with ruff ruff check web/src tests` — no new lint findings introduced by this plan.
- Manual browser sanity (optional, not gating): `uv run --with streamlit streamlit run app/app.py` is unaffected; the web explorer under `web/` shows compact dropdown options like `DATACITE44 → DCTERMS` and `RDAMSC_C1 → DST_RDAMSC_C1 (rdamsc_c1)`, and the heading above the rules table reads e.g. `DataCite 4.4 to Dublin Core Terms` when that crosswalk is selected and switches immediately on selection change.
</verification>

<success_criteria>
- Dropdown labels are compact and never contain expanded standard names.
- Every RDAMSC dropdown option ends with `(rdamsc_c*)`; the `datacite44_to_dcterms` option does NOT redundantly repeat its `id` in parens.
- A visible heading above the rules table displays the selected crosswalk's `display_name`, updated on every selection change, including initial load.
- Natural sort order and `display_name` provenance from 260827-g0f are intact.
- New/updated smoke tests pass; no persistence-free, export, or curation invariants are weakened.
- Only `web/src/main.js`, `web/index.html`, `web/src/style.css`, and `tests/test_curation_ui_smoke.py` are modified. No backend or dependency changes.
</success_criteria>

<output>
Create `.planning/quick/260827-gnm-use-concise-acronym-only-crosswalk-label/260827-gnm-SUMMARY.md` when done
</output>
