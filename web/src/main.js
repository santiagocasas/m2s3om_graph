import { RecordId, Surreal } from 'surrealdb';
import { createWasmEngines } from '@surrealdb/wasm';
import * as curation from './curation.js';
import { loadGraphData } from './graph-loader.js';
import { renderConvertPage } from './convert.js';
import { initGraphPage } from './graph.js';

const statusEl = document.getElementById('status');
const selectEl = document.getElementById('crosswalk-select');
const exportBtn = document.getElementById('export-tsv-btn');
const exportSssomBtn = document.getElementById('export-sssom-btn');
const tbody = document.querySelector('#rules-table tbody');

const appContainer = document.getElementById('app');
const nav = document.getElementById('nav');
const currentCrosswalkTitleEl = document.getElementById('current-crosswalk-title');
const currentCrosswalkSubtitleEl = document.getElementById('current-crosswalk-subtitle');
function navigate(page) {
  if (nav) {
    [...nav.children].forEach(btn => btn.classList.toggle('active', btn.dataset.page === page));
  }
  if (page === 'convert') {
    document.getElementById('controls')?.remove();
    document.getElementById('status')?.remove();
    document.getElementById('rules-table-container')?.remove();
    document.getElementById('no-writeback-notice')?.remove();
    currentCrosswalkTitleEl?.remove();
    currentCrosswalkSubtitleEl?.remove();
    renderConvertPage();
    return;
  }
  if (page === 'graph') {
    document.getElementById('controls')?.remove();
    document.getElementById('status')?.remove();
    document.getElementById('rules-table-container')?.remove();
    document.getElementById('no-writeback-notice')?.remove();
    currentCrosswalkTitleEl?.remove();
    currentCrosswalkSubtitleEl?.remove();
    initGraphPage();
    return;
  }
  if (page === 'overview') {
    document.getElementById('controls')?.remove();
    document.getElementById('status')?.remove();
    document.getElementById('rules-table-container')?.remove();
    document.getElementById('no-writeback-notice')?.remove();
    currentCrosswalkTitleEl?.remove();
    currentCrosswalkSubtitleEl?.remove();
    renderOverviewPage();
    return;
  }
  if (page === 'documentation') {
    document.getElementById('controls')?.remove();
    document.getElementById('status')?.remove();
    document.getElementById('rules-table-container')?.remove();
    document.getElementById('no-writeback-notice')?.remove();
    currentCrosswalkTitleEl?.remove();
    currentCrosswalkSubtitleEl?.remove();
    renderDocumentationPage();
    return;
  }
  // Reset explorer view
  location.reload();
}
if (nav) {
  nav.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-page]');
    if (!btn) return;
    navigate(btn.dataset.page);
  });
}

let currentCrosswalkRecord = null;
const candidateRows = new WeakMap();
const candidateData = new WeakMap();

function renderOverviewPage() {
  if (appContainer) {
    appContainer.innerHTML = `
      <section class="panel">
        <div class="eyebrow">Evidence-based metadata crosswalk workbench</div>
        <h2>Turning scattered metadata mapping documents into reusable crosswalks.</h2>
        <p class="lead">m2s3om_graph harvests mapping records from the RDA Metadata Standards Catalog, retrieves the original mapping artifacts, extracts field-level rules, and publishes them as transparent SSSOM crosswalks that can be inspected, visualized, and applied to real metadata records.</p>
        <div class="metrics-grid">
          <div class="metric"><strong>37</strong><span>RDAMSC crosswalks processed</span></div>
          <div class="metric"><strong>23 (62.2%)</strong><span>ready with SSSOM output</span></div>
          <div class="metric"><strong>1072</strong><span>actual SSSOM mapping rows</span></div>
          <div class="metric"><strong>11/24</strong><span>artifacts fetched</span></div>
        </div>
        <div class="callout"><strong>Why it matters:</strong> metadata standards are well documented, but crosswalks are often buried in PDFs, XSL files, web pages, and legacy tables. This project makes those mappings explicit, versioned, machine-readable, and connected in a graph.</div>
      </section>
      <section class="section cards">
        <div class="card"><h3>Evidence pipeline</h3><p>Each mapping is tied back to source artifacts and frozen pipeline outputs, so a crosswalk can be audited rather than treated as an opaque model answer.</p></div>
        <div class="card"><h3>Hybrid extraction</h3><p><strong>2</strong> deterministic and <strong>21</strong> LLM-assisted graph edges show how rule extraction can combine stable patterns with language-model assistance.</p></div>
        <div class="card"><h3>Crosswalk network</h3><p><strong>20</strong> standards in the crosswalk network</p><p><strong>23</strong> crosswalk edges in the network</p><p>The graph view highlights domains, standard families, and high-volume mappings for exploration and presentation.</p></div>
      </section>
    `;
  }
}

function renderDocumentationPage() {
  if (appContainer) {
    appContainer.innerHTML = `
      <section class="panel">
        <div class="eyebrow">How to use the project</div>
        <h2>Documentation</h2>
        <p class="lead">The project has three practical layers: a Vite-based web app for browsing and converting metadata, a reproducible RDAMSC pipeline for extracting SSSOM crosswalks, and a GitLab Pages site built from the same Vite app for communicating the results.</p>
      </section>
      <section class="section two-col">
        <div class="card">
          <h3>1. Install and run the web app</h3>
          <p>Run the Vite explorer locally. It starts from the committed SSSOM files and the embedded SurrealDB WASM, so the app runs entirely in the browser without re-ingesting the catalog.</p>
          <pre><code>uv sync
cd web
npm install
npm run dev</code></pre>
          <p>Open <code>http://localhost:5173</code> and use the tabs: <strong>Overview</strong>, <strong>Explore</strong>, <strong>Graph</strong>, <strong>Convert</strong>, and <strong>Docs</strong>.</p>
        </div>
        <div class="card">
          <h3>2. Run a fast conversion smoke test</h3>
          <p>This checks the package entrypoint and applies the bundled mapping rules to a synthetic record.</p>
          <pre><code>uv run python -m m2s3om_graph.cli.main demo-convert</code></pre>
          <p>The command reports how many rules were applied and which source fields remained unmapped.</p>
        </div>
      </section>
      <section class="section two-col">
        <div class="card">
          <h3>3. Regenerate frozen statistics</h3>
          <p>If the RDAMSC pipeline has already run, freeze the current status, plots, CSVs, and SSSOM provenance into <code>exports/pipeline/latest/</code>.</p>
          <pre><code>make pipeline-freeze</code></pre>
          <p>Use the explicit command below when you need to point at non-default status, log, or output locations.</p>
          <pre><code>uv run python scripts/rdamsc_pipeline_stats.py freeze   --status-file .local/rdamsc_pipeline_status.json   --output-dir exports/pipeline/latest   --sssom-dir exports/sssom   --pipeline-log .local/bootstrap_rdamsc.log   --plots</code></pre>
        </div>
        <div class="card">
          <h3>4. Build and serve the Vite app for GitLab Pages</h3>
          <p>The Pages site is now the Vite app. Build it and serve the static output.</p>
          <pre><code>cd web
npm install
npm run build
python -m http.server 8000 --directory dist</code></pre>
          <p>Open <code>http://localhost:8000</code> to inspect the built site before pushing changes.</p>
        </div>
      </section>
      <section class="section cards">
        <div class="card"><h3>Crosswalk extraction</h3><p>The pipeline synchronizes RDAMSC mapping records, downloads source artifacts, converts them to text/markdown, extracts mapping rules with deterministic and LLM-assisted strategies, and exports SSSOM TSV files.</p></div>
        <div class="card"><h3>Conversion engine</h3><p>Records are parsed into an intermediate representation, matched against SSSOM rules, and serialized back to supported target formats such as Dublin Core or DataCite XML.</p></div>
        <div class="card"><h3>Graph visualization</h3><p>The crosswalk network groups standards by topic, merges known aliases for visualization, weights edges by mapped field count, and can be exported as SVG or PNG for posters and slides.</p></div>
      </section>
      <section class="section card">
        <h3>Further reading</h3>
        <p>Use <code>README.md</code> for commands, <code>CODEBASE_WALKTHROUGH.md</code> for architecture, <code>POSTER_BRIEF.md</code> for the public-facing story, <code>TALK_RESULTS_SNAPSHOT.md</code> for frozen numbers, and <code>BENCHMARKING.md</code> for evaluation workflows.</p>
      </section>
    `;
  }
}

function updateExportButton() {
  const count = curation.getAcceptedCandidates().length;
  if (exportBtn instanceof HTMLButtonElement) {
    exportBtn.textContent = `Export accepted (${count}) as TSV`;
    exportBtn.disabled = count === 0;
  }
  const sssomCount = currentCrosswalkRecord
    ? curation.getAcceptedCandidates().filter((entry) => entry.crosswalkId === currentCrosswalkRecord.id).length
    : 0;
  if (exportSssomBtn instanceof HTMLButtonElement) {
    exportSssomBtn.textContent = `Export SSSOM (${sssomCount})`;
    exportSssomBtn.disabled = sssomCount === 0 || !currentCrosswalkRecord;
  }
}

async function main() {
  statusEl.textContent = 'Starting embedded SurrealDB (WASM)...';

  let db = new Surreal({ engines: createWasmEngines() });

  // IndexedDB can be unavailable in restricted browser contexts. Keep the
  // explorer usable with an in-memory database when that happens.
  try {
    await db.connect('indxdb://m2s3om');
    await db.use({ namespace: 'm2s3om', database: 'crosswalks' });
  } catch (error) {
    console.warn('IndexedDB SurrealDB storage unavailable; using memory storage.', error);
    db = new Surreal({ engines: createWasmEngines() });
    await db.connect('mem://m2s3om');
    await db.use({ namespace: 'm2s3om', database: 'crosswalks' });
  }

  statusEl.textContent = 'Loading crosswalk data...';
  const data = await loadGraphData(db, '/data/crosswalk_graph.json');

  const orderedCrosswalks = populateSelect(data.crosswalks, data.standards);
  statusEl.textContent =
    `Loaded ${orderedCrosswalks.length} crosswalks across ${data.standards.length} standards. ` +
    'Running entirely in your browser, no server involved.';
  statusEl.classList.remove('bad');

  selectEl.addEventListener('change', () => showCrosswalk(db, selectEl.value));
  if (exportBtn instanceof HTMLButtonElement) {
    exportBtn.addEventListener('click', () => {
      if (!exportBtn.disabled) {
        curation.downloadAcceptedTsv();
      }
    });
  }
  if (exportSssomBtn instanceof HTMLButtonElement) {
    exportSssomBtn.addEventListener('click', () => {
      if (!exportSssomBtn.disabled && currentCrosswalkRecord) {
        curation.downloadSssomTsv(currentCrosswalkRecord.id);
      }
    });
  }
  if (!tbody.dataset.curationBound) {
    tbody.addEventListener('click', handleTbodyClick);
    tbody.dataset.curationBound = '1';
  }

  if (orderedCrosswalks.length > 0) {
    selectEl.value = orderedCrosswalks[0].id;
    await showCrosswalk(db, orderedCrosswalks[0].id);
  }

  updateExportButton();
}

export function naturalKey(id) {
  const parts = String(id).split(/(\d+)/).filter(Boolean);
  return parts.map((part) => (/^\d+$/.test(part) ? [0, Number(part)] : [1, part]));
}

function compareNaturalKeys(left, right) {
  const maxLength = Math.max(left.length, right.length);
  for (let index = 0; index < maxLength; index += 1) {
    const leftPart = left[index];
    const rightPart = right[index];
    if (!leftPart) return -1;
    if (!rightPart) return 1;
    if (leftPart[0] !== rightPart[0]) {
      return leftPart[0] - rightPart[0];
    }
    if (leftPart[1] < rightPart[1]) return -1;
    if (leftPart[1] > rightPart[1]) return 1;
  }
  return 0;
}

function buildCompactCrosswalkToken(standardId) {
  return String(standardId ?? '')
    .trim()
    .replace(/^standard:/, '')
    .replace(/^dst_/, '')
    .toUpperCase();
}

export function buildCrosswalkLabel(cw) {
  const sourceAcronym = String(cw?.source_acronym ?? '').trim();
  const targetAcronym = String(cw?.target_acronym ?? '').trim();
  const crosswalkId = String(cw?.id ?? '').trim();
  const rdamscId = /^rdamsc_c\d+$/i.test(crosswalkId);

  if (sourceAcronym && targetAcronym) {
    const canonicalLabel = `${sourceAcronym} → ${targetAcronym}`;
    return rdamscId ? `${canonicalLabel} (${crosswalkId})` : canonicalLabel;
  }

  const sourceToken = buildCompactCrosswalkToken(cw?.source);
  const targetToken = buildCompactCrosswalkToken(cw?.target);
  const rawTargetToken = String(cw?.target ?? '').trim().replace(/^standard:/, '').toUpperCase();
  const displayTargetToken =
    sourceToken && targetToken === sourceToken && rawTargetToken.startsWith('DST_')
      ? rawTargetToken
      : targetToken;
  const compactLabel =
    sourceToken && displayTargetToken
      ? `${sourceToken} → ${displayTargetToken}`
      : `${String(cw?.source ?? '')} → ${String(cw?.target ?? '')}`;
  const sourceId = String(cw?.source ?? '').trim();
  const targetId = String(cw?.target ?? '').trim();

  if (!crosswalkId || crosswalkId === `${sourceId}_to_${targetId}`) {
    return compactLabel;
  }

  return `${compactLabel} (${crosswalkId})`;
}

function formatCrosswalkSubtitle(cw) {
  const sourceAcronym = String(cw?.source_acronym ?? '').trim();
  const sourceExpansion = String(cw?.source_expansion ?? '').trim();
  const targetAcronym = String(cw?.target_acronym ?? '').trim();
  const targetExpansion = String(cw?.target_expansion ?? '').trim();

  if (!sourceAcronym && !targetAcronym) {
    return '';
  }

  const sourceText = sourceExpansion ? `${sourceAcronym} (${sourceExpansion})` : sourceAcronym;
  const targetText = targetExpansion ? `${targetAcronym} (${targetExpansion})` : targetAcronym;
  return `${sourceText} → ${targetText}`;
}

export function populateSelect(crosswalks, standards) {
  selectEl.innerHTML = '';
  if (crosswalks.length === 0) {
    renderRules([]);
    return [];
  }

  const orderedCrosswalks = [...crosswalks].sort((left, right) =>
    compareNaturalKeys(naturalKey(left.id), naturalKey(right.id)),
  );

  for (const cw of orderedCrosswalks) {
    const opt = document.createElement('option');
    opt.value = cw.id;
    opt.textContent = buildCrosswalkLabel(cw);
    selectEl.appendChild(opt);
  }

  return orderedCrosswalks;
}

async function showCrosswalk(db, crosswalkId) {
  if (!crosswalkId) {
    currentCrosswalkRecord = null;
    if (currentCrosswalkTitleEl instanceof HTMLElement) {
      currentCrosswalkTitleEl.textContent = '';
    }
    if (currentCrosswalkSubtitleEl instanceof HTMLElement) {
      currentCrosswalkSubtitleEl.textContent = '';
    }
    renderRules([]);
    updateExportButton();
    return;
  }
  const result = await db.select(new RecordId('crosswalk', crosswalkId));
  const record = Array.isArray(result) ? result[0] : result;
  currentCrosswalkRecord = record ?? null;
  if (currentCrosswalkTitleEl instanceof HTMLElement) {
    currentCrosswalkTitleEl.textContent = record ? buildCrosswalkLabel(record) : '';
  }
  if (currentCrosswalkSubtitleEl instanceof HTMLElement) {
    currentCrosswalkSubtitleEl.textContent = record ? formatCrosswalkSubtitle(record) : '';
  }
  renderRules(record?.rules ?? []);
  updateExportButton();
}

function renderRules(rules) {
  tbody.innerHTML = '';
  if (rules.length === 0) {
    const tr = document.createElement('tr');
    tr.className = 'empty-state';
    tr.innerHTML = `
      <td colspan="7"><strong>No mapping rules</strong><br><span class="muted">This crosswalk has no defined rules. Verify the export pipeline ran successfully.</span></td>
    `;
    tbody.appendChild(tr);
    return;
  }

  for (const rule of rules) {
    const tr = document.createElement('tr');
    const confidence = typeof rule.confidence === 'number' ? rule.confidence.toFixed(2) : '';
    const sourceText = rule.source_display || (rule.source_paths ?? []).join(' | ');
    const targetPaths = Array.isArray(rule.target_paths) ? rule.target_paths : [];
    const targetText =
      targetPaths.length === 0
        ? '<em>missing</em>'
        : escapeHtml(rule.target_display || targetPaths.join(' | '));
    const shouldSuggest = !Array.isArray(rule.target_paths) || rule.target_paths.length === 0;
    const classes = [];
    if (rule.semantic_loss === true) {
      classes.push('bad');
    }
    if (targetPaths.length === 0) {
      classes.push('warn');
    }
    tr.className = classes.join(' ');
    tr.innerHTML = `
      <td>${escapeHtml(sourceText)}</td>
      <td>${targetText}</td>
      <td>${escapeHtml(rule.mapping_type ?? '')}</td>
      <td class="${confidence && Number(confidence) >= 0.9 ? 'good' : ''}">${confidence}</td>
      <td><span class="strategy-badge strategy-${escapeHtml(rule.strategy ?? '')}">${escapeHtml(rule.strategy ?? '')}</span></td>
      <td>${rule.semantic_loss === true ? '<span class="loss-icon" aria-label="semantic loss detected">⚠</span>' : ''}</td>
      <td class="actions-cell">${shouldSuggest ? `<button type="button" class="suggest-btn" data-source-field="${escapeHtml(sourceText)}">Suggest candidate mappings</button>` : '<span class="muted"></span>'}</td>
    `;
    tbody.appendChild(tr);
  }

  restoreAcceptedCandidateRows();
  updateExportButton();
}

async function handleSuggestClick(button) {
  if (!currentCrosswalkRecord) {
    return;
  }

  const triggerRow = button.closest('tr');
  if (!(triggerRow instanceof HTMLTableRowElement)) {
    return;
  }

  removeCandidateRows(triggerRow);
  const sourceField = button.dataset.sourceField ?? '';
  insertSuggestModeRow(triggerRow, sourceField);
}

async function runLlmSuggest(triggerRow, sourceField, button) {
  if (!currentCrosswalkRecord) {
    return;
  }

  removeCandidateRows(triggerRow);
  button.disabled = true;
  button.textContent = 'Loading…';

  const sourceStandard = String(currentCrosswalkRecord.source ?? '').replace(/^standard:/, '');
  const targetStandard = String(currentCrosswalkRecord.target ?? '').replace(/^standard:/, '');
  const targetSchemaFields = [
    ...new Set((currentCrosswalkRecord.rules || []).flatMap((rule) => rule.target_paths || [])),
  ];

  try {
    const candidates = await curation.postSuggestRequest({
      sourceStandard,
      targetStandard,
      sourceField,
      targetSchemaFields,
    });

    renderCandidateRows(triggerRow, sourceField, candidates);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    const errorRow = document.createElement('tr');
    errorRow.className = 'candidate-error';
    errorRow.dataset.sourceField = sourceField;
    errorRow.innerHTML = `<td colspan="7">${escapeHtml(message)}</td>`;
    triggerRow.insertAdjacentElement('afterend', errorRow);
  } finally {
    button.disabled = false;
    button.textContent = 'Suggest candidate mappings';
  }
}

function handleTbodyClick(event) {
  if (!(event.target instanceof Element)) {
    return;
  }
  const button = event.target.closest('button');
  if (!(button instanceof HTMLButtonElement)) {
    return;
  }

  if (button.classList.contains('suggest-btn')) {
    handleSuggestClick(button);
    return;
  }

  if (button.classList.contains('suggest-mode-llm')) {
    handleSuggestModeLlmClick(button);
    return;
  }

  if (button.classList.contains('suggest-mode-manual')) {
    handleSuggestModeManualClick(button);
    return;
  }

  if (button.classList.contains('suggest-mode-cancel') || button.classList.contains('manual-form-cancel')) {
    const controlRow = button.closest('tr');
    if (controlRow instanceof HTMLTableRowElement) {
      controlRow.remove();
    }
    return;
  }

  if (button.classList.contains('manual-form-submit')) {
    handleManualFormSubmit(button);
    return;
  }

  if (button.classList.contains('accept-btn') || button.classList.contains('reject-btn')) {
    handleDecisionClick(button);
  }
}

function handleSuggestModeLlmClick(button) {
  const controlRow = button.closest('tr');
  if (!(controlRow instanceof HTMLTableRowElement)) {
    return;
  }

  const triggerRow = controlRow.previousElementSibling;
  if (!(triggerRow instanceof HTMLTableRowElement)) {
    return;
  }

  const sourceField = controlRow.dataset.sourceField ?? '';
  const suggestButton = triggerRow.querySelector('.suggest-btn');
  if (!(suggestButton instanceof HTMLButtonElement)) {
    return;
  }

  runLlmSuggest(triggerRow, sourceField, suggestButton);
}

function handleSuggestModeManualClick(button) {
  const controlRow = button.closest('tr');
  if (!(controlRow instanceof HTMLTableRowElement)) {
    return;
  }

  const triggerRow = controlRow.previousElementSibling;
  if (!(triggerRow instanceof HTMLTableRowElement)) {
    return;
  }

  const sourceField = controlRow.dataset.sourceField ?? '';
  insertManualFormRow(triggerRow, sourceField);
}

function insertSuggestModeRow(triggerRow, sourceField) {
  const chooserRow = document.createElement('tr');
  chooserRow.className = 'suggest-mode-row';
  chooserRow.dataset.sourceField = sourceField;
  chooserRow.innerHTML = `
    <td colspan="7">
      <button type="button" class="suggest-mode-llm">Ask LLM</button>
      <button type="button" class="suggest-mode-manual">Enter manually</button>
      <button type="button" class="suggest-mode-cancel">Cancel</button>
    </td>
  `;
  triggerRow.insertAdjacentElement('afterend', chooserRow);
}

function insertManualFormRow(triggerRow, sourceField) {
  removeCandidateRows(triggerRow);

  const manualRow = document.createElement('tr');
  manualRow.className = 'manual-form-row';
  manualRow.dataset.sourceField = sourceField;
  manualRow.innerHTML = `
    <td colspan="7">
      <form class="manual-form">
        <label>
          Source path
          <input type="text" data-field="source_path" value="" />
        </label>
        <label>
          Target path
          <input type="text" data-field="target_path" />
        </label>
        <label>
          Mapping type
          <select data-field="mapping_type">
            <option value="direct">direct</option>
            <option value="conditional">conditional</option>
            <option value="missing">missing</option>
            <option value="aggregation">aggregation</option>
          </select>
        </label>
        <label>
          Confidence
          <input type="number" data-field="confidence" min="0" max="1" step="0.05" value="1.0" />
        </label>
        <label>
          Evidence
          <input type="text" data-field="evidence" />
        </label>
        <label>
          Notes
          <input type="text" data-field="notes" />
        </label>
        <div class="manual-form-actions">
          <button type="button" class="manual-form-submit">Add candidate</button>
          <button type="button" class="manual-form-cancel">Cancel</button>
        </div>
      </form>
    </td>
  `;
  triggerRow.insertAdjacentElement('afterend', manualRow);
  const sourceInput = manualRow.querySelector('[data-field="source_path"]');
  if (sourceInput instanceof HTMLInputElement) {
    sourceInput.value = sourceField;
  }
}

function handleManualFormSubmit(button) {
  const manualRow = button.closest('tr');
  if (!(manualRow instanceof HTMLTableRowElement)) {
    return;
  }

  const triggerRow = manualRow.previousElementSibling;
  if (!(triggerRow instanceof HTMLTableRowElement)) {
    return;
  }

  const sourceField = manualRow.dataset.sourceField ?? '';
  const manualCandidate = buildManualCandidate(manualRow);
  manualRow.remove();
  renderCandidateRows(triggerRow, sourceField, [manualCandidate]);
}

function buildManualCandidate(manualRow) {
  const sourcePath = getManualFieldValue(manualRow, 'source_path');
  const targetPath = getManualFieldValue(manualRow, 'target_path');
  const mappingType = getManualFieldValue(manualRow, 'mapping_type');
  const confidenceValue = Number(getManualFieldValue(manualRow, 'confidence'));
  const evidence = getManualFieldValue(manualRow, 'evidence');
  const notes = getManualFieldValue(manualRow, 'notes');

  return {
    source_path: sourcePath,
    target_path: targetPath,
    mapping_type: mappingType,
    confidence: Number.isNaN(confidenceValue) ? 1.0 : confidenceValue,
    evidence,
    notes,
  };
}

function getManualFieldValue(manualRow, field) {
  const input = manualRow.querySelector(`[data-field="${field}"]`);
  if (input instanceof HTMLInputElement || input instanceof HTMLSelectElement || input instanceof HTMLTextAreaElement) {
    return input.value;
  }
  return '';
}

function renderCandidateRows(triggerRow, sourceField, candidates) {
  const list = Array.isArray(candidates) ? candidates : [];
  removeCandidateRows(triggerRow);
  const survivingAcceptedRows = candidateRows.get(triggerRow) || [];
  let insertAfter = survivingAcceptedRows.at(-1) ?? triggerRow;
  const renderedRows = [...survivingAcceptedRows];

  for (const candidate of list) {
    if (currentCrosswalkRecord && curation.getDecision(currentCrosswalkRecord.id, sourceField, candidate)?.status === 'accepted') {
      continue;
    }

    const row = createCandidateRowElement(sourceField, candidate, renderedRows.length);
    candidateData.set(row, candidate);
    insertAfter.insertAdjacentElement('afterend', row);
    insertAfter = row;
    renderedRows.push(row);
  }

  if (renderedRows.length > 0) {
    candidateRows.set(triggerRow, renderedRows);
    return;
  }

  candidateRows.delete(triggerRow);
}

function handleDecisionClick(button) {
  const candidateRow = button.closest('.candidate-row');
  if (!(candidateRow instanceof HTMLTableRowElement)) {
    return;
  }

  const triggerRow = candidateRow.previousElementSibling;
  if (!(triggerRow instanceof HTMLTableRowElement)) {
    return;
  }

  const sourceField = candidateRow.dataset.sourceField ?? '';
  const candidates = candidateRows.get(triggerRow) || [];
  const index = Number(button.dataset.candidateIdx ?? '-1');
  const candidate = candidates[index] ?? candidateData.get(candidateRow);
  if (!candidate || !currentCrosswalkRecord) {
    return;
  }

  if (button.classList.contains('accept-btn')) {
    curation.acceptCandidate(currentCrosswalkRecord.id, sourceField, candidate);
    markCandidateRow(candidateRow, 'accepted', 'Accepted ✓');
  } else {
    curation.rejectCandidate(currentCrosswalkRecord.id, sourceField, candidate);
    markCandidateRow(candidateRow, 'rejected', 'Rejected ✗');
  }

  updateExportButton();
}

function markCandidateRow(row, status, label) {
  row.classList.remove('accepted', 'rejected');
  row.classList.add(status);
  const buttons = row.querySelectorAll('button');
  buttons.forEach((button) => {
    button.disabled = true;
  });
  const selectedButton = row.querySelector(`.${status === 'accepted' ? 'accept-btn' : 'reject-btn'}`);
  if (selectedButton instanceof HTMLButtonElement) {
    selectedButton.textContent = label;
  }
}

function createCandidateRowElement(sourceField, candidate, index) {
  const row = document.createElement('tr');
  row.className = 'candidate-row';
  row.dataset.sourceField = sourceField;
  row.innerHTML = `
    <td colspan="7">
      <div class="candidate-fields">
        <span><span class="field-label">Source:</span> <span class="field-value">${escapeHtml(candidate?.source_path ?? '')}</span></span>
        <span><span class="field-label">Target:</span> <span class="field-value">${escapeHtml(candidate?.target_path ?? '(none)')}</span></span>
        <span><span class="field-label">Type:</span> <span class="field-value">${escapeHtml(candidate?.mapping_type ?? '')}</span></span>
        <span><span class="field-label">Confidence:</span> <span class="field-value">${formatConfidence(candidate?.confidence)}</span></span>
        <span><span class="field-label">Evidence:</span> <span class="field-value">${escapeHtml(candidate?.evidence ?? '')}</span></span>
        <span><span class="field-label">Notes:</span> <span class="field-value">${escapeHtml(candidate?.notes ?? '')}</span></span>
        <button type="button" class="accept-btn" data-candidate-idx="${index}">Accept</button>
        <button type="button" class="reject-btn" data-candidate-idx="${index}">Reject</button>
      </div>
    </td>
  `;
  return row;
}

function restoreAcceptedCandidateRows() {
  if (!currentCrosswalkRecord) {
    return;
  }

  const acceptedEntries = curation
    .getAcceptedCandidates()
    .filter((entry) => entry.crosswalkId === currentCrosswalkRecord.id);

  for (const entry of acceptedEntries) {
    const selector = `.suggest-btn[data-source-field="${CSS.escape(entry.sourceField)}"]`;
    const suggestButton = tbody.querySelector(selector);
    if (!(suggestButton instanceof HTMLButtonElement)) {
      console.debug('Skipping accepted row restore; no suggest button found for source field', entry.sourceField);
      continue;
    }

    const triggerRow = suggestButton.closest('tr');
    if (!(triggerRow instanceof HTMLTableRowElement)) {
      continue;
    }

    const candidate = entry.candidate ?? {};
    const existingRows = candidateRows.get(triggerRow) || [];
    const row = createCandidateRowElement(entry.sourceField, candidate, existingRows.length);
    candidateData.set(row, candidate);
    const insertAfter = existingRows.at(-1) ?? triggerRow;
    insertAfter.insertAdjacentElement('afterend', row);
    existingRows.push(row);
    candidateRows.set(triggerRow, existingRows);
    markCandidateRow(row, 'accepted', 'Accepted ✓');
  }
}

function removeCandidateRows(triggerRow) {
  let next = triggerRow.nextElementSibling;
  const survivingRows = [];
  while (
    next &&
    (next.classList.contains('candidate-row') ||
      next.classList.contains('candidate-error') ||
      next.classList.contains('suggest-mode-row') ||
      next.classList.contains('manual-form-row'))
  ) {
    const current = next;
    next = next.nextElementSibling;
    if (current.classList.contains('accepted')) {
      survivingRows.push(current);
      continue;
    }
    current.remove();
  }
  if (survivingRows.length > 0) {
    candidateRows.set(triggerRow, survivingRows);
    return;
  }
  candidateRows.delete(triggerRow);
}

function formatConfidence(value) {
  return typeof value === 'number' ? value.toFixed(2) : escapeHtml(String(value ?? ''));
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}

main().catch((err) => {
  console.error(err);
  statusEl.textContent =
    'Data unavailable: failed to load crosswalk_graph.json — expected at ' +
    'public/data/crosswalk_graph.json. Run the export script before building.';
  statusEl.classList.add('bad');
});
