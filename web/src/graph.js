// ── Constants ──────────────────────────────────────────────────────────────

const GRAPH_DATA_URL = '/data/crosswalk_graph.json';

// ── Styles ─────────────────────────────────────────────────────────────────

const styles = `
.graph-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  overflow: hidden;
}

.graph-header {
  padding: 1rem;
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
}

.graph-header h2 {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
}

.graph-header p {
  margin: 0;
  color: #6b7280;
  font-size: 0.875rem;
}

.graph-container {
  flex: 1;
  display: flex;
  overflow: hidden;
  position: relative;
  background: #ffffff;
}

#cy {
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.graph-sidebar {
  width: 300px;
  border-left: 1px solid #e5e7eb;
  background: #fafafa;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.graph-sidebar h3 {
  margin: 0;
  padding: 1rem 1rem 0.5rem;
  font-size: 1rem;
  font-weight: 600;
}

.graph-sidebar-content {
  flex: 1;
  overflow: auto;
  padding: 0.5rem 1rem;
}

.graph-sidebar-empty {
  color: #6b7280;
  font-size: 0.875rem;
  text-align: center;
  padding: 2rem 1rem;
}

.node-details {
  display: none;
}

.node-details.visible {
  display: block;
}

.node-details .node-kind {
  display: inline-block;
  font-size: 0.75rem;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid #e5e7eb;
  background: #fff;
  color: #111827;
  margin-bottom: 0.5rem;
}

.node-details .node-info {
  display: grid;
  grid-template-columns: 80px 1fr;
  gap: 4px 12px;
  font-size: 0.875rem;
  margin-top: 0.5rem;
}

.node-details .node-info .key {
  color: #6b7280;
  word-break: break-word;
}

.node-details .node-info .value {
  word-break: break-word;
}

.node-details .node-neighbors {
  margin-top: 1rem;
  font-size: 0.875rem;
}

.node-details .node-neighbors ul {
  margin: 4px 0 0 18px;
  padding: 0;
}

.node-details .node-neighbors li {
  margin: 2px 0;
  word-break: break-word;
}

.graph-sidebar-footer {
  padding: 1rem;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}

.graph-sidebar-footer details {
  margin-top: 0.5rem;
}

.graph-sidebar-footer details > summary {
  list-style: none;
  cursor: pointer;
  user-select: none;
  font-size: 0.875rem;
  color: #374151;
  padding: 6px 10px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  background: #f9fafb;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.graph-sidebar-footer details > summary::-webkit-details-marker {
  display: none;
}

.graph-sidebar-footer details > summary::after {
  content: '▼';
  font-size: 0.75rem;
  transform: rotate(180deg);
  transition: transform 0.2s;
}

.graph-sidebar-footer details[open] > summary::after {
  transform: rotate(90deg);
}

.graph-sidebar-footer details[open] > summary {
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
}

.graph-sidebar-footer details > div {
  padding: 10px;
  border: 1px solid #e5e7eb;
  border-top: none;
  border-radius: 0 0 6px 6px;
  background: #fff;
  margin-top: -1px;
}

.graph-controls {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding: 0.5rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.graph-controls button,
.graph-controls select {
  padding: 6px 10px;
  font-size: 0.8125rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}

.graph-controls button:hover,
.graph-controls select:hover {
  border-color: #9ca3af;
}

.graph-controls button:active {
  background: #f3f4f6;
}

#graph-status {
  font-size: 0.8125rem;
  color: #374151;
  padding: 0.5rem 1rem;
  background: #f9fafb;
  border-bottom: 1px solid #e5e7eb;
}

.graph-fullscreen-btn {
  display: none;
  position: absolute;
  top: 0.5rem;
  right: 0.5rem;
  z-index: 10;
  padding: 6px 10px;
  font-size: 0.8125rem;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  background: #fff;
  cursor: pointer;
}

.graph-fullscreen-btn.visible {
  display: block;
}

@media (max-width: 900px) {
  .graph-sidebar {
    width: 100%;
    height: 40vh;
    border-left: none;
    border-top: 1px solid #e5e7eb;
  }
}
`;

// ── DOM elements ───────────────────────────────────────────────────────────

let cy = null;
let baseElements = null;
let kindInfo = new Map();
let activeKinds = new Set();
let graphHasCoords = false;

// ── Helpers ────────────────────────────────────────────────────────────────

function escapeHtml(str) {
  return String(str)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function truncateLabel(s, max = 20) {
  if (typeof s !== 'string') return '';
  const t = s.trim();
  return t.length <= max ? t : t.slice(0, max) + '...';
}

// ── Graph loading ──────────────────────────────────────────────────────────

function parseGraphologyJson(json) {
  const nodes = Array.isArray(json.nodes) ? json.nodes : [];
  const edges = Array.isArray(json.edges) ? json.edges : [];
  const elements = [];

  for (const n of nodes) {
    if (!n || typeof n.id !== 'string') continue;
    const attrs = n.attributes || {};
    const label = attrs.label || n.id;
    const kind = attrs.kind || attrs.type || '';
    const color = typeof attrs.color === 'string' && attrs.color ? attrs.color : '#64748b';

    elements.push({
      group: 'nodes',
      data: {
        id: n.id,
        label: label,
        truncatedLabel: truncateLabel(label),
        fullLabel: label,
        kind: kind,
        color: color,
        size: attrs.size || 10,
        origX: typeof attrs.x === 'number' ? attrs.x : 0,
        origY: typeof attrs.y === 'number' ? attrs.y : 0,
        ...Object.fromEntries(
          Object.entries(attrs).filter(([k]) =>
            !['label', 'fullLabel', 'kind', 'color', 'x', 'y', 'size', 'type'].includes(k)
          )
        ),
      },
    });
  }

  for (let i = 0; i < edges.length; i++) {
    const e = edges[i] || {};
    if (typeof e.source !== 'string' || typeof e.target !== 'string') continue;
    const eAttrs = e.attributes || {};
    const key = typeof e.key === 'string' ? e.key : `e${i}`;

    elements.push({
      group: 'edges',
      data: {
        id: key,
        source: e.source,
        target: e.target,
        color: typeof eAttrs.color === 'string' && eAttrs.color ? eAttrs.color : '#9ca3af',
        edgeSize: typeof eAttrs.size === 'number' ? Math.max(0.5, eAttrs.size) : 1.5,
        ...Object.fromEntries(
          Object.entries(eAttrs).filter(([k]) => !['color', 'size'].includes(k))
        ),
      },
    });
  }

  return elements;
}

function computeKindInfo(elements) {
  const counts = new Map();
  const colors = new Map();
  for (const el of elements) {
    if (el.group !== 'nodes') continue;
    const attrs = el.data || {};
    const k = attrs.kind || '(unknown)';
    counts.set(k, (counts.get(k) || 0) + 1);
    if (!colors.has(k) && typeof attrs.color === 'string' && attrs.color) {
      colors.set(k, attrs.color);
    }
  }
  const info = new Map();
  Array.from(counts.keys()).sort((a, b) => a.localeCompare(b)).forEach((k) => {
    info.set(k, { count: counts.get(k) || 0, color: colors.get(k) || '#64748b' });
  });
  return info;
}

function applySizeByDegree(elements) {
  const degree = new Map();
  for (const el of elements) {
    if (el.group !== 'edges') continue;
    const src = el.data.source;
    const tgt = el.data.target;
    degree.set(src, (degree.get(src) || 0) + 1);
    degree.set(tgt, (degree.get(tgt) || 0) + 1);
  }
  for (const el of elements) {
    if (el.group !== 'nodes') continue;
    const d = el.data;
    const deg = degree.get(d.id) || 0;
    const kind = d.kind || '';
    let base = 6;
    if (kind === 'service') base = 18;
    else if (kind === 'organization') base = 10;
    else if (kind === 'source') base = 7;
    d.size = (base + Math.min(6, deg * 0.6)) * 4;
  }
}

function loadGraphData() {
  return fetch(GRAPH_DATA_URL)
    .then(res => {
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return res.json();
    })
    .then(json => {
      const elements = parseGraphologyJson(json);
      applySizeByDegree(elements);
      baseElements = elements;

      const nodeEls = elements.filter(e => e.group === 'nodes');
      const coordCount = nodeEls.filter(e => e.data.origX !== 0 || e.data.origY !== 0).length;
      graphHasCoords = coordCount > nodeEls.length * 0.5;

      kindInfo = computeKindInfo(baseElements);
      activeKinds = new Set(kindInfo.keys());

      return elements;
    });
}

function buildStylesheet() {
  return [
    {
      selector: 'node',
      style: {
        'background-color': 'data(color)',
        'label': 'data(truncatedLabel)',
        'font-size': '10px',
        'font-family': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': '3px',
        'color': '#1f2933',
        'text-background-color': '#ffffff',
        'text-background-opacity': 0.8,
        'text-background-padding': '2px',
        'width': 'data(size)',
        'height': 'data(size)',
        'border-color': '#ffffff',
        'border-width': 1.5,
      },
    },
    {
      selector: 'node:selected',
      style: {
        'border-color': '#2563eb',
        'border-width': 3,
      },
    },
    {
      selector: 'node.hovered',
      style: {
        'overlay-color': '#6b7280',
        'overlay-padding': 4,
        'overlay-opacity': 0.12,
      },
    },
    {
      selector: 'edge',
      style: {
        'line-color': 'data(color)',
        'width': 'data(edgeSize)',
        'target-arrow-color': 'data(color)',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'arrow-scale': 0.7,
        'opacity': 0.7,
      },
    },
  ];
}

function rebuildAndRender() {
  if (!cy) return;

  const allowedIds = new Set();
  const nodes = [];
  const edges = [];

  for (const el of baseElements) {
    if (el.group !== 'nodes') continue;
    const kind = el.data.kind || '(unknown)';
    if (!activeKinds.has(kind)) continue;
    allowedIds.add(el.data.id);
    nodes.push(el);
  }

  for (const el of baseElements) {
    if (el.group !== 'edges') continue;
    const src = el.data.source;
    const tgt = el.data.target;
    if (!allowedIds.has(src) || !allowedIds.has(tgt)) continue;
    edges.push(el);
  }

  const elements = [...nodes, ...edges];

  if (elements.filter(e => e.group === 'nodes').length === 0) {
    cy.elements().remove();
    document.getElementById('graph-status').textContent = 'No nodes selected. Enable at least one kind.';
    return;
  }

  cy.elements().remove();
  cy.add(elements);

  cy.layout({
    name: graphHasCoords ? 'preset' : 'cose',
    positions: graphHasCoords
      ? (node) => ({ x: node.data('origX') || 0, y: -(node.data('origY') || 0) })
      : undefined,
    fit: true,
    padding: 60,
  }).run();

  const nodeCount = elements.filter(e => e.group === 'nodes').length;
  const edgeCount = elements.filter(e => e.group === 'edges').length;
  document.getElementById('graph-status').textContent = `Rendered: ${nodeCount} nodes, ${edgeCount} edges.`;
}

// ── Sidebar rendering ──────────────────────────────────────────────────────

function renderSidebarForNode(nodeData) {
  const attrs = nodeData;
  const kind = attrs.kind || '';
  const fullLabel = attrs.fullLabel || attrs.label || attrs.id || '';

  const sidebarContent = document.querySelector('.graph-sidebar-content');
  const emptyEl = document.querySelector('.graph-sidebar-empty');
  const detailsEl = document.querySelector('.node-details');

  emptyEl.style.display = 'none';
  detailsEl.style.display = 'none';

  if (kind) {
    detailsEl.innerHTML = `
      <div class="node-kind">${escapeHtml(kind)}</div>
      <div class="node-info">
        <span class="key">ID</span><span class="value">${escapeHtml(String(attrs.id || ''))}</span>
        <span class="key">Label</span><span class="value">${escapeHtml(fullLabel)}</span>
      </div>
    `;

    if (cy) {
      const nodeEl = cy.getElementById(attrs.id);
      const neighbors = nodeEl.neighborhood().nodes();
      const maxNeighbors = 20;
      const shown = neighbors.slice(0, maxNeighbors);

      let neighborsHtml = '';
      if (shown.length > 0) {
        neighborsHtml = `
          <ul>
            ${shown.map(n => {
              const d = n.data();
              const text = d.fullLabel || d.label || n.id();
              return `<li>${escapeHtml(text)}</li>`;
            }).join('')}
          </ul>
        `;
      }

      detailsEl.innerHTML += `
        <div class="node-neighbors">
          <strong>${escapeHtml(fullLabel)}</strong> connects to ${neighbors.length} node(s)
          ${neighborsHtml}
        </div>
      `;
    }

    detailsEl.style.display = 'block';
  } else {
    emptyEl.style.display = 'block';
  }
}

// ── Legend rendering ───────────────────────────────────────────────────────

function renderLegend() {
  const legendContent = document.querySelector('.legend-content');
  if (!legendContent) return;

  let nodesHtml = '';
  for (const [k, meta] of kindInfo.entries()) {
    nodesHtml += `
      <div class="legend-item" style="display:flex;align-items:center;gap:8px;margin:6px 0;font-size:13px;">
        <span class="legend-swatch" style="width:10px;height:10px;border-radius:3px;background:${meta.color};border:1px solid rgba(0,0,0,0.15);flex:0 0 auto;"></span>
        <span class="legend-name" style="flex:1 1 auto;">${escapeHtml(k)}</span>
        <span class="legend-count" style="color:#6b7280;font-variant-numeric:tabular-nums;">${meta.count}</span>
      </div>
    `;
  }

  let edgesHtml = '';
  if (baseElements) {
    const seenStrategies = new Map();
    for (const el of baseElements) {
      if (el.group !== 'edges') continue;
      const d = el.data;
      const strategy = d.strategy || 'unknown';
      if (!seenStrategies.has(strategy)) {
        seenStrategies.set(strategy, {
          label: d.relationship || strategy,
          color: d.color || '#9ca3af',
        });
      }
    }

    for (const [strategy, { label, color }] of seenStrategies.entries()) {
      edgesHtml += `
        <div class="legend-item" style="display:flex;align-items:center;gap:8px;margin:6px 0;font-size:13px;">
          <svg width="28" height="12" style="flex:0 0 auto;">
            <line x1="2" y1="6" x2="26" y2="6" stroke="${color}" stroke-width="2.5" stroke-linecap="round"></line>
          </svg>
          <span class="legend-name" style="flex:1 1 auto;">${escapeHtml(label)}</span>
        </div>
      `;
    }
  }

  legendContent.innerHTML = `
    <div style="margin-bottom:10px;border-bottom:1px solid #e5e7eb;padding-bottom:8px;font-size:12px;font-weight:600;color:#111827;">Node categories</div>
    <div style="display:grid;gap:4px;margin-bottom:12px;">${nodesHtml}</div>
    <div style="margin-bottom:10px;border-bottom:1px solid #e5e7eb;padding-bottom:8px;font-size:12px;font-weight:600;color:#111827;">Edge types</div>
    <div style="display:grid;gap:4px;">${edgesHtml}</div>
  `;
}

// ── Kind filter UI ─────────────────────────────────────────────────────────

function renderKindFilter() {
  const kindList = document.querySelector('.kind-list');
  if (!kindList) return;

  kindList.innerHTML = '';
  for (const [k, meta] of kindInfo.entries()) {
    const row = document.createElement('div');
    row.className = 'kind-item';
    row.style.cssText = 'display:flex;align-items:center;gap:10px;font-size:13px;color:#111827;margin:4px 0;';

    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = activeKinds.has(k);
    cb.dataset.kind = k;

    const sw = document.createElement('span');
    sw.className = 'kind-swatch';
    sw.style.cssText = `width:10px;height:10px;border-radius:3px;background:${meta.color};border:1px solid rgba(0,0,0,0.15);flex:0 0 auto;`;

    const name = document.createElement('span');
    name.className = 'kind-name';
    name.style.cssText = 'flex:1 1 auto;word-break:break-word;';
    name.textContent = k;

    const count = document.createElement('span');
    count.className = 'kind-count';
    count.style.cssText = 'color:#6b7280;font-variant-numeric:tabular-nums;';
    count.textContent = meta.count;

    row.appendChild(cb);
    row.appendChild(sw);
    row.appendChild(name);
    row.appendChild(count);
    kindList.appendChild(row);

    cb.addEventListener('change', () => {
      const kind = cb.dataset.kind;
      if (!kind) return;
      if (cb.checked) activeKinds.add(kind);
      else activeKinds.delete(kind);
      rebuildAndRender();
    });
  }
}

// ── Fullscreen toggle ──────────────────────────────────────────────────────

function toggleFullscreen() {
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(err => {
      console.error(`Error attempting to enable fullscreen: ${err.message}`);
    });
  } else {
    document.exitFullscreen();
  }
}

function updateFullscreenButton() {
  const btn = document.getElementById('fullscreen-btn');
  if (!btn) return;

  if (document.fullscreenElement) {
    btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>';
  } else {
    btn.innerHTML = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>';
  }
}

// ── Layout controls ────────────────────────────────────────────────────────

function setLayout(kind) {
  if (!cy) return;

  let layoutOpts;
  if (kind === 'preset') {
    layoutOpts = {
      name: 'preset',
      positions: (node) => ({ x: node.data('origX') || 0, y: -(node.data('origY') || 0) }),
      fit: true,
      padding: 60,
    };
  } else if (kind === 'cose') {
    layoutOpts = {
      name: 'cose',
      animate: true,
      animationDuration: 800,
      fit: true,
      padding: 60,
    };
  } else if (kind === 'circle') {
    layoutOpts = {
      name: 'circle',
      animate: true,
      fit: true,
      padding: 60,
    };
  } else {
    return;
  }

  cy.layout(layoutOpts).run();
}

// ── Export functions ───────────────────────────────────────────────────────

function exportAsSvg() {
  if (!cy) {
    alert('Graph not loaded yet.');
    return;
  }
  const svgContent = cy.svg({ full: true, scale: 1, bg: '#ffffff' });
  const blob = new Blob([svgContent], { type: 'image/svg+xml' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `m2s3om_crosswalk_graph_${new Date().toISOString().slice(0, 10)}.svg`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 250);
}

function exportAsPng() {
  if (!cy) {
    alert('Graph not loaded yet.');
    return;
  }
  const dataUrl = cy.png({ full: true, scale: 2, bg: '#ffffff' });
  const a = document.createElement('a');
  a.href = dataUrl;
  a.download = `m2s3om_crosswalk_graph_${new Date().toISOString().slice(0, 10)}.png`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// ── Register cytoscape-svg plugin ──────────────────────────────────────────

if (typeof cytoscapeSvg !== 'undefined') {
  cytoscape.use(cytoscapeSvg);
}

// ── Initialization ─────────────────────────────────────────────────────────

function initGraphPage() {
  if (typeof cytoscape === 'undefined') {
    alert('Cytoscape.js is not loaded. Please wait a moment and try again.');
    return;
  }
  
  // Clear app container first
  const container = document.getElementById('app');
  if (container) {
    container.innerHTML = '';
  }
  
  // Remove any existing controls/status elements
  document.getElementById('controls')?.remove();
  document.getElementById('status')?.remove();
  document.getElementById('rules-table-container')?.remove();
  document.getElementById('no-writeback-notice')?.remove();
  // Inject styles
  if (!document.getElementById('graph-page-styles')) {
    const styleEl = document.createElement('style');
    styleEl.id = 'graph-page-styles';
    styleEl.textContent = styles;
    document.head.appendChild(styleEl);
  }

  // Create DOM structure
  const container = document.getElementById('app');
  if (!container) return;

  container.innerHTML = `
    <div class="graph-page">
      <header class="graph-header">
        <h2>Graph Visualization</h2>
        <p>Browse crosswalk relationships as an interactive network graph.</p>
      </header>

      <div class="graph-controls">
        <select id="layout-select">
          <option value="preset" ${graphHasCoords ? 'selected' : ''}>Preset (x/y)</option>
          <option value="cose" ${!graphHasCoords ? 'selected' : ''}>COSE (Force)</option>
          <option value="circle">Circular</option>
        </select>
        <button id="reset-view">Reset view</button>
        <button id="export-svg">Export SVG</button>
        <button id="export-png">Export PNG</button>
        <button id="fullscreen-btn" class="graph-fullscreen-btn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
          </svg>
        </button>
      </div>

      <div id="graph-status">Loading graph data...</div>

      <div class="graph-container">
        <div id="cy"></div>
        <aside class="graph-sidebar">
          <h3>Node details</h3>
          <div class="graph-sidebar-content">
            <div class="graph-sidebar-empty">Click a node to see its attributes.</div>
            <div class="node-details"></div>
          </div>
          <div class="graph-sidebar-footer">
            <details id="legend-panel">
              <summary><span>Legend</span></summary>
              <div class="legend-content"></div>
            </details>
            <details id="kind-filter">
              <summary><span>Node kinds</span></summary>
              <div class="kind-list" style="display:grid;gap:4px;"></div>
            </details>
          </div>
        </aside>
      </div>
    </div>
  `;

  // Initialize Cytoscape
  const loadPromise = loadGraphData();

  loadPromise.then(elements => {
    cy = cytoscape({
      container: document.getElementById('cy'),
      elements: elements,
      style: buildStylesheet(),
      layout: {
        name: graphHasCoords ? 'preset' : 'cose',
        positions: graphHasCoords
          ? (node) => ({ x: node.data('origX') || 0, y: -(node.data('origY') || 0) })
          : undefined,
        fit: true,
        padding: 60,
      },
      minZoom: 0.05,
      maxZoom: 8,
    });

    // ── Event handlers ─────────────────────────────────────────────────

    cy.on('mouseover', 'node', (evt) => {
      const node = evt.target;
      node.addClass('hovered');
    });

    cy.on('mouseout', 'node', (evt) => {
      evt.target.removeClass('hovered');
    });

    cy.on('tap', 'node', (evt) => {
      const d = evt.target.data();
      renderSidebarForNode(d);
    });

    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        document.querySelector('.graph-sidebar-content .graph-sidebar-empty').style.display = 'block';
        document.querySelector('.node-details').style.display = 'none';
      }
    });

    // ── UI controls ────────────────────────────────────────────────────

    document.getElementById('reset-view').addEventListener('click', () => {
      cy && cy.fit(undefined, 60);
    });

    document.getElementById('layout-select').addEventListener('change', (e) => {
      setLayout(e.target.value);
    });

    document.getElementById('export-svg').addEventListener('click', exportAsSvg);
    document.getElementById('export-png').addEventListener('click', exportAsPng);

    document.getElementById('fullscreen-btn').addEventListener('click', toggleFullscreen);

    document.addEventListener('fullscreenchange', updateFullscreenButton);

    // ── Render UI ──────────────────────────────────────────────────────

    renderLegend();
    renderKindFilter();
    rebuildAndRender();

    // Show fullscreen button after a short delay
    setTimeout(() => {
      document.getElementById('fullscreen-btn').classList.add('visible');
    }, 1000);
  }).catch(err => {
    document.getElementById('graph-status').textContent = `Error loading graph: ${err.message}`;
    document.getElementById('app').innerHTML += `<pre style="color:#b91c1c;padding:1rem;">${escapeHtml(err.stack || err.message)}</pre>`;
  });
}

// ── Export ─────────────────────────────────────────────────────────────────

export { initGraphPage };
