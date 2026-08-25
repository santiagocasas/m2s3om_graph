import { RecordId, Surreal } from 'surrealdb';
import { createWasmEngines } from '@surrealdb/wasm';
import * as curation from './curation.js';
import { loadGraphData } from './graph-loader.js';
import { renderConvertPage } from './convert.js';

const statusEl = document.getElementById('status');
const selectEl = document.getElementById('crosswalk-select');
const exportBtn = document.getElementById('export-tsv-btn');
const tbody = document.querySelector('#rules-table tbody');

const appContainer = document.getElementById('app');
const nav = document.getElementById('nav');
function navigate(page) {
  if (nav) {
    [...nav.children].forEach(btn => btn.classList.toggle('active', btn.dataset.page === page));
  }
  if (page === 'convert') {
    document.getElementById('controls')?.remove();
    document.getElementById('status')?.remove();
    document.getElementById('rules-table-container')?.remove();
    document.getElementById('no-writeback-notice')?.remove();
    renderConvertPage();
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

function updateExportButton() {
  const count = curation.getAcceptedCandidates().length;
  if (exportBtn instanceof HTMLButtonElement) {
    exportBtn.textContent = `Export accepted (${count}) as TSV`;
    exportBtn.disabled = count === 0;
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

  populateSelect(data.crosswalks);
  statusEl.textContent =
    `Loaded ${data.crosswalks.length} crosswalks across ${data.standards.length} standards. ` +
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
  if (!tbody.dataset.curationBound) {
    tbody.addEventListener('click', handleTbodyClick);
    tbody.dataset.curationBound = '1';
  }

  if (data.crosswalks.length > 0) {
    selectEl.value = data.crosswalks[0].id;
    await showCrosswalk(db, data.crosswalks[0].id);
  }

  updateExportButton();
}

function populateSelect(crosswalks) {
  selectEl.innerHTML = '';
  if (crosswalks.length === 0) {
    renderRules([]);
    return;
  }
  for (const cw of crosswalks) {
    const opt = document.createElement('option');
    opt.value = cw.id;
    opt.textContent = `${cw.source} -> ${cw.target} (${cw.id})`;
    selectEl.appendChild(opt);
  }
}

async function showCrosswalk(db, crosswalkId) {
  if (!crosswalkId) {
    currentCrosswalkRecord = null;
    renderRules([]);
    return;
  }
  const result = await db.select(new RecordId('crosswalk', crosswalkId));
  const record = Array.isArray(result) ? result[0] : result;
  currentCrosswalkRecord = record ?? null;
  renderRules(record?.rules ?? []);
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

  if (button.classList.contains('accept-btn') || button.classList.contains('reject-btn')) {
    handleDecisionClick(button);
  }
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
  button.disabled = true;
  button.textContent = 'Loading…';

  const sourceField = button.dataset.sourceField ?? '';
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
    button.disabled = false;
    button.textContent = 'Suggest candidate mappings';
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    const errorRow = document.createElement('tr');
    errorRow.className = 'candidate-error';
    errorRow.dataset.sourceField = sourceField;
    errorRow.innerHTML = `<td colspan="7">${escapeHtml(message)}</td>`;
    triggerRow.insertAdjacentElement('afterend', errorRow);
    button.disabled = false;
    button.textContent = 'Suggest candidate mappings';
  }
}

function renderCandidateRows(triggerRow, sourceField, candidates) {
  const list = Array.isArray(candidates) ? candidates : [];
  removeCandidateRows(triggerRow);
  candidateRows.set(triggerRow, []);

  for (let index = list.length - 1; index >= 0; index -= 1) {
    const candidate = list[index];
    const row = document.createElement('tr');
    row.className = 'candidate-row';
    row.dataset.sourceField = sourceField;
    candidateRows.set(triggerRow, [row, ...(candidateRows.get(triggerRow) || [])]);
    candidateData.set(row, candidate);
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
    triggerRow.insertAdjacentElement('afterend', row);
  }
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

function removeCandidateRows(triggerRow) {
  let next = triggerRow.nextElementSibling;
  while (next && (next.classList.contains('candidate-row') || next.classList.contains('candidate-error'))) {
    const current = next;
    next = next.nextElementSibling;
    current.remove();
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
