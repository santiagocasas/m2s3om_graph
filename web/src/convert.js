export async function renderConvertPage() {
  const app = document.getElementById('app');
  if (!app) return;

  app.innerHTML = `
    <div class="page">
      <h1>Convert a Record</h1>
      <p class="muted">Paste a metadata record and convert between supported formats using the authoritative SSSOM routes.</p>
      <div class="grid">
        <div>
          <label>Source format</label>
          <select id="src-format">
            <option value="oai_dc_xml">OAI Dublin Core XML</option>
            <option value="datacite_xml">DataCite XML</option>
            <option value="marcxml">MARCXML</option>
          </select>
        </div>
        <div>
          <label>Target format</label>
          <select id="tgt-format">
            <option value="datacite_xml">DataCite XML</option>
            <option value="oai_dc_xml">OAI Dublin Core XML</option>
            <option value="marcxml">MARCXML</option>
          </select>
        </div>
      </div>
      <label>Source XML</label>
      <textarea id="src-xml" rows="12" placeholder="Paste XML here..."></textarea>
      <button id="convert-btn" class="primary">Convert</button>
      <div id="result" class="result"></div>
    </div>
  `;

  const btn = document.getElementById('convert-btn');
  const result = document.getElementById('result');

  btn.addEventListener('click', async () => {
    const sourceXml = document.getElementById('src-xml').value.trim();
    const sourceFormat = document.getElementById('src-format').value;
    const targetFormat = document.getElementById('tgt-format').value;

    if (!sourceXml) {
      result.innerHTML = '<p class="error">Please provide source XML.</p>';
      return;
    }

    result.innerHTML = '<p class="muted">Converting…</p>';

    try {
      const resp = await fetch('/convert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source_xml: sourceXml, source_format: sourceFormat, target_format: targetFormat })
      });
      if (!resp.ok) {
        const err = await resp.text();
        throw new Error(err || 'Conversion failed');
      }
      const data = await resp.json();
      result.innerHTML = `
        <h3>Converted XML</h3>
        <pre>${escapeHtml(data.target_xml)}</pre>
        <p class="muted">Applied rules: ${data.applied_rule_ids.length}, Unmapped: ${data.unmapped_fields.length}</p>
      `;
    } catch (e) {
      result.innerHTML = `<p class="error">Error: ${escapeHtml(e.message)}</p>`;
    }
  });
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str ?? '';
  return div.innerHTML;
}
