# kaigraph

`kaigraph` is an evidence-based metadata crosswalk workbench.

It now supports:

- syncing all mapping records from the RDAMSC API,
- ingesting easy mapping artifact formats (PDF/HTML/TXT/XML/XSL),
- extracting mapping rules with Blablador-backed AI assistance,
- writing authoritative `.sssom.tsv` files to disk,
- applying conversion rules from SSSOM in the Streamlit conversion tab.

## Quickstart

```bash
uv sync
uv run --with pytest pytest
uv run streamlit run app/app.py
uv run python -m kaigraph.cli.main demo-convert
```

## Run with local SurrealDB (Docker)

Fastest way (starts SurrealDB + Streamlit in fast mode, no heavy bootstrap):

```bash
./scripts/run_app_local.sh
```

The launcher waits for SurrealDB sign-in readiness. If readiness fails, startup aborts with a clear message.

Optional wait tuning:

```bash
KAIGRAPH_DB_WAIT_ATTEMPTS=60 KAIGRAPH_DB_WAIT_DELAY=1 ./scripts/run_app_local.sh
```

To run a quick catalog metadata sync on startup:

```bash
KAIGRAPH_SYNC_RDAMSC_CATALOG=1 ./scripts/run_app_local.sh
```

To run full verbose bootstrap on startup:

```bash
KAIGRAPH_BOOTSTRAP_RDAMSC=1 ./scripts/run_app_local.sh
```

Bootstrap logs are written to:

- `.local/bootstrap_rdamsc.log`

In the app, use the **Pipeline** tab to re-run the full process (or a single mapping) and watch step-by-step logs.

Manual mode:

```bash
./scripts/run_surrealdb_local.sh

export KAIGRAPH_USE_SURREAL=1
export KAIGRAPH_DB_URL=ws://localhost:8000/rpc
export KAIGRAPH_DB_NS=kaigraph
export KAIGRAPH_DB_NAME=crosswalk
export KAIGRAPH_DB_USER=root
export KAIGRAPH_DB_PASSWORD=root
```

Optional stop command:

```bash
./scripts/stop_surrealdb_local.sh
```

## RDAMSC sync + ingest

```bash
# 1) sync metadata catalog
uv run python -m kaigraph.cli.main sync-rdamsc

# 2) ingest all supported artifact docs and emit SSSOM files
uv run python -m kaigraph.cli.main sync-rdamsc --with-ingest

# 3) sync catalog and generate missing SSSOM files (skip existing)
uv run python -m kaigraph.cli.main bootstrap-rdamsc

# or ingest one crosswalk already in store
uv run python -m kaigraph.cli.main ingest-rdamsc --crosswalk-id rdamsc_c5
```

SSSOM output directory defaults to:

- `exports/sssom/`

## Freeze pipeline outputs for commit

Use this section to avoid confusion between `pipeline-freeze` and `pipeline-stats`.

If you already ran the pipeline (for example in Streamlit) and want commit-ready outputs,
run only:

```bash
make pipeline-freeze
```

`pipeline-freeze` reads the existing status file and writes:

- `exports/pipeline/latest/` (status JSON copy, stats JSON/CSV, artifact CSV, plots, run metadata, log snapshot)
- `exports/sssom/GENERATED_FROM_PIPELINE.md`
- `exports/sssom/generation_manifest.json`

`generation_manifest.json` includes checksums for committed `.sssom.tsv` files plus git/env provenance.

You do **not** need to run `pipeline-stats` after `pipeline-freeze`.

If you need to run the pipeline again before freezing:

```bash
make pipeline-run-freeze
```

If you only want refreshed analytics files (no rerun, no SSSOM provenance rewrite), use:

```bash
make pipeline-stats
```

About `--force`: it re-ingests crosswalks that are already `ready`.
Use it only when you intentionally want to regenerate outputs with current pipeline/model behavior.

## Package layout

- `src/kaigraph/rdamsc`: RDAMSC API sync + artifact ingestion
- `src/kaigraph/sssom.py`: authoritative SSSOM read/write
- `src/kaigraph/ingest`: mapping artifact parsers (including PDF)
- `src/kaigraph/transform`: IR parsers, deterministic rule application, serializers
- `src/kaigraph/oai`: OAI-PMH client and metadata format discovery
- `src/kaigraph/db`: schema and repository layer
- `src/kaigraph/candidates`: AI-assisted candidate mapping suggestions (non-baseline)
- `app/app.py`: Streamlit app with 5 tabs (Crosswalks, Pipeline, System, Benchmark, Convert)

## Current status

This repository currently provides:

- RDAMSC mapping catalog sync (`/api2/c`)
- artifact ingestion converted to markdown via MarkItDown
- markdown artifact/chunk ingestion into KG with provenance
- deterministic conversion engine with ambiguity/loss flags
- conversion driven by SSSOM rows in the conversion tab
- OAI-PMH integration for one-record conversion workflows
- AI-assisted candidate suggestions using Blablador-compatible endpoints (fallback heuristic)
