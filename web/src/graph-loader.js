/**
 * Loads a crosswalk graph export (standards + crosswalks with rules) into
 * an already-connected SurrealDB instance (WASM-embedded, mem:// or indxdb://).
 *
 * Expected shape:
 * {
 *   "standards": [{ "id": "datacite", "name": "..." }, ...],
 *   "crosswalks": [
 *     { "id": "rdamsc_c5", "source": "datacite", "target": "dublin_core", "rules": [...] },
 *     ...
 *   ]
 * }
 *
 * Record IDs containing chars outside [a-zA-Z0-9_] are backtick-escaped via
 * escapeId() so both standards and crosswalks stay queryable in SurrealQL.
 */
function escapeId(raw) {
  return /[^a-zA-Z0-9_]/.test(String(raw)) ? '`' + raw + '`' : String(raw);
}

export async function loadGraphData(db, jsonUrl) {
  const res = await fetch(jsonUrl);
  if (!res.ok) {
    throw new Error(`Failed to fetch graph data (${res.status}): ${jsonUrl}`);
  }
  const data = await res.json();

  for (const standard of data.standards) {
    await db.create(`standard:${escapeId(standard.id)}`, { name: standard.name });
  }

  for (const crosswalk of data.crosswalks) {
    await db.create(`crosswalk:${escapeId(crosswalk.id)}`, {
      source: `standard:${escapeId(crosswalk.source)}`,
      target: `standard:${escapeId(crosswalk.target)}`,
      rules: crosswalk.rules,
    });
  }

  return data;
}
