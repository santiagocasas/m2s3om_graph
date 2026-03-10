# Benchmarking Kaigraph

The Streamlit benchmark tab has been removed so the demo app stays focused on the three workflows that are presentation-critical: browse, pipeline, and convert.

For benchmark and statistics work, use the CLI and the frozen pipeline exports.

## Quick Checks

### Fast fixture benchmark

```bash
uv run python -m kaigraph.cli.main benchmark-fixture
```

This is the fastest smoke test for the benchmark/report pipeline.

## Pipeline-Level Statistics

If you already ran the RDAMSC pipeline and want reproducible statistics and plots:

```bash
make pipeline-freeze
```

This writes:

- `exports/pipeline/latest/rdamsc_stats_summary.json`
- `exports/pipeline/latest/rdamsc_crosswalks.csv`
- `exports/pipeline/latest/rdamsc_artifacts.csv`
- `exports/pipeline/latest/plots/`
- `exports/sssom/GENERATED_FROM_PIPELINE.md`
- `exports/sssom/generation_manifest.json`

## Read The Current Snapshot

Start with these files:

- `TALK_RESULTS_SNAPSHOT.md`
- `exports/pipeline/latest/rdamsc_stats_summary.json`
- `exports/pipeline/latest/rdamsc_pipeline_status.json`
- `exports/sssom/GENERATED_FROM_PIPELINE.md`

## Recommended Slide Numbers

- total crosswalks
- ready / failed_unreachable / failed_parse counts and rates
- artifact fetch success rate
- top successful hosts
- top failing hosts
- one concrete recovery case (`rdamsc_c38`)

## Current Limitation

There is not yet a dedicated CLI command for full remote eLib batch benchmarking with record-id lists. For now, rely on:

1. the fixture benchmark command for fast regression checks
2. frozen pipeline statistics for presentation-ready charts
3. direct Python/CLI scripting around `kaigraph.benchmark.run_elib_benchmark` if needed
