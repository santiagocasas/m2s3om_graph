import { Surreal } from 'surrealdb';
import { createWasmEngines } from '@surrealdb/wasm';
import { loadGraphData } from './graph-loader.js';

const statusEl = document.getElementById('status');
const selectEl = document.getElementById('crosswalk-select');
const tbody = document.querySelector('#rules-table tbody');

async function main() {
  statusEl.textContent = 'Starting embedded SurrealDB (WASM)...';

  const db = new Surreal({ engines: createWasmEngines() });

  // indxdb:// persists across reloads via IndexedDB. Swap to mem:// for a
  // fresh, throwaway database on every page load instead.
  await db.connect('indxdb://m2s3om');
  await db.use({ namespace: 'm2s3om', database: 'crosswalks' });

  statusEl.textContent = 'Loading crosswalk data...';
  const data = await loadGraphData(db, './data/crosswalk_graph.json');

  populateSelect(data.crosswalks);
  statusEl.textContent =
    `Loaded ${data.crosswalks.length} crosswalks across ${data.standards.length} standards. ` +
    'Running entirely in your browser, no server involved.';
  statusEl.classList.remove('bad');

  selectEl.addEventListener('change', () => showCrosswalk(db, selectEl.value));

  if (data.crosswalks.length > 0) {
    selectEl.value = data.crosswalks[0].id;
    await showCrosswalk(db, data.crosswalks[0].id);
  }
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
    renderRules([]);
    return;
  }
  const result = await db.select(`crosswalk:${crosswalkId}`);
  const record = Array.isArray(result) ? result[0] : result;
  renderRules(record?.rules ?? []);
}

function renderRules(rules) {
  tbody.innerHTML = '';
  if (rules.length === 0) {
    const tr = document.createElement('tr');
    tr.className = 'empty-state';
    tr.innerHTML = `
      <td colspan="6"><strong>No mapping rules</strong><br><span class="muted">This crosswalk has no defined rules. Verify the export pipeline ran successfully.</span></td>
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
    `;
    tbody.appendChild(tr);
  }
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}

main().catch((err) => {
  console.error(err);
  statusEl.textContent = 'Data unavailable: failed to load crosswalk_graph.json — expected at public/data/crosswalk_graph.json. Run the export script before building.';
  statusEl.classList.add('bad');
});
