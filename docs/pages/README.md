# GitLab Pages site source

This directory contains the source assets for the generated GitLab Pages site.

Build locally with:

```bash
python scripts/build_pages.py
```

The build writes a static site to `public/`, which is what the GitLab Pages job publishes.

The generator reads current frozen project outputs from:

- `exports/pipeline/latest/rdamsc_stats_summary.json`
- `exports/pipeline/latest/run_metadata.json`
- `exports/sssom/*.sssom.tsv`
- `exports/graph/crosswalk_graph.json`
- `data/crosswalk_network.json`
- graph visualizer files from `exports/graph_visualizer_web/` or `graph-visualizer/web/`

Do not edit `public/` by hand; rebuild it from repository data.
