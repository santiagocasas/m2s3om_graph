import { Surreal } from 'surrealdb';
import { surrealdbWasmEngines } from '@surrealdb/wasm';
import { loadGraphData } from './graph-loader.js';

const statusEl = document.getElementById('status');
const selectEl = document.getElementById('crosswalk-select');
const tbody = document.querySelector('#rules-table tbody');

async function main() {
  statusEl.textContent = 'Starting embedded SurrealDB (WASM)...';

  const db = new Surreal({ engines: surrealdbWasmEngines() });

  // indxdb:// persists across reloads via IndexedDB. Swap to mem:// for a
  // fresh, throwaway database on every page load instead.
  await db.connect('indxdb://m2s3om');
  await db.use({ namespace: 'm2s3om', database: 'crosswalks' });

  statusEl.textContent = 'Loading crosswalk data...';
  // TODO: replace with the real export path once generated, e.g.
  // './data/crosswalk_graph.json'
  const data = await loadGraphData(db, './data/crosswalk_graph_sample.json');

  populateSelect(data.crosswalks);
  statusEl.textContent =
    `Loaded ${data.crosswalks.length} crosswalks across ${data.standards.length} standards. ` +
    'Running entirely in your browser, no server involved.';

  selectEl.addEventListener('change', () => showCrosswalk(db, selectEl.value));

  if (data.crosswalks.length > 0) {
    selectEl.value = data.crosswalks[0].id;
    await showCrosswalk(db, data.crosswalks[0].id);
  }
}

function populateSelect(crosswalks) {
  selectEl.innerHTML = '';
  for (const cw of crosswalks) {
    const opt = document.createElement('option');
    opt.value = cw.id;
    opt.textContent = `${cw.source} -> ${cw.target} (${cw.id})`;
    selectEl.appendChild(opt);
  }
}

async function showCrosswalk(db, crosswalkId) {
  const result = await db.select(`crosswalk:${crosswalkId}`);
  const record = Array.isArray(result) ? result[0] : result;
  renderRules(record?.rules ?? []);
}

function renderRules(rules) {
  tbody.innerHTML = '';
  for (const rule of rules) {
    const tr = document.createElement('tr');
    const confidence = typeof rule.confidence === 'number' ? rule.confidence.toFixed(2) : '';
    tr.innerHTML = `
      <td>${escapeHtml(rule.source_path)}</td>
      <td>${rule.target_path ? escapeHtml(rule.target_path) : '<em>missing</em>'}</td>
      <td>${escapeHtml(rule.mapping_type ?? '')}</td>
      <td>${confidence}</td>
      <td>${escapeHtml(rule.evidence ?? '')}</td>
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
  statusEl.textContent = `Error: ${err.message}`;
});
