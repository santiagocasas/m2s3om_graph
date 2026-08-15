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
 * Note: record IDs with dashes or other non-alphanumeric characters need
 * backtick-escaping in SurrealQL (e.g. crosswalk:`rdamsc-c5`).
 */
export async function loadGraphData(db, jsonUrl) {
  const res = await fetch(jsonUrl);
  if (!res.ok) {
    throw new Error(`Failed to fetch graph data (${res.status}): ${jsonUrl}`);
  }
  const data = await res.json();

  for (const standard of data.standards) {
    await db.create(`standard:${standard.id}`, { name: standard.name });
  }

  for (const crosswalk of data.crosswalks) {
    await db.create(`crosswalk:${crosswalk.id}`, {
      source: `standard:${crosswalk.source}`,
      target: `standard:${crosswalk.target}`,
      rules: crosswalk.rules,
    });
  }

  return data;
}
