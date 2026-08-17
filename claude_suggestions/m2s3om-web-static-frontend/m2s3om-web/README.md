# M²S³OM-graph — static Crosswalk Explorer

A proof-of-concept static frontend that browses your extracted SSSOM crosswalk
graph entirely client-side, no backend, using SurrealDB's WASM-embedded engine
(`@surrealdb/wasm`) with IndexedDB persistence.

## What this proves

That the Browse experience (select a crosswalk, see its rules, confidence
scores, evidence) can run as a pure static site on GitLab Pages, with the
actual graph data shipped as a JSON file and queried live in the visitor's
browser. No server, no secrets, no CORS issues, since nothing leaves the
browser.

## Local setup

```bash
npm install surrealdb @surrealdb/wasm
npm install -D vite
npm run dev
```

Open the local URL Vite prints. You should see two sample crosswalks
(DataCite→Dublin Core, MARC→Dublin Core) load and render.

If `@surrealdb/wasm` fails to resolve at the version npm picks by default,
try the `@alpha` tag instead (`npm install @surrealdb/wasm@alpha`), some
SurrealDB docs reference both; check whichever resolves cleanly for you.

## Replacing the sample data with your real export

`public/data/crosswalk_graph_sample.json` is a stand-in. You need a script
(Python is fine, this can live in your existing pipeline repo) that reads
your committed SSSOM TSV files plus your standards list and emits one JSON
file in this shape:

```json
{
  "standards": [{ "id": "...", "name": "..." }],
  "crosswalks": [
    { "id": "...", "source": "...", "target": "...", "rules": [ ... ] }
  ]
}
```

Each rule object should match your existing SSSOM-derived schema
(`source_path`, `target_path`, `mapping_type`, `confidence`, `evidence`).
Drop the generated file at `public/data/crosswalk_graph.json` and update the
path in `src/main.js` (marked with a `TODO`).

Record IDs (`crosswalk:<id>`, `standard:<id>`) need to be valid SurrealQL
identifiers. If any of your crosswalk IDs contain dashes, either swap them
for underscores at export time or escape them with backticks in
`graph-loader.js`, plain dashes will break the query.

## Wiring into your existing GitLab Pages site

This was built standalone so it's easy to test in isolation. To merge it
into your existing site (the one with the project info and graph
visualization already live):

1. Drop this whole folder in as `web/` at your repo root, alongside whatever
   currently produces your existing Pages content.
2. Use `.gitlab-ci.yml.snippet` as a starting point for the `pages` job, but
   merge it with your current CI config rather than running two competing
   `pages` jobs, only one `public/` artifact is allowed.
3. Link to this page from your existing landing page (or replace the old
   static graph image with a link straight into this interactive version).

## Known limitation

This only covers the Browse/visualization experience. Running the
extraction pipeline and converting live records still need a real backend
(API keys, arbitrary external fetches that hit CORS), that's the FastAPI
and Streamlit pieces in the sibling folders.
