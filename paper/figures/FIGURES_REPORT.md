# Table 2 figure data — 50677355 (2026-09-29)

Commit: `506773552eca426ae2182964c42e949459e730dc`  
Commit date: `2026-09-29`  
Regeneration: `uv run python scripts/make_paper_figures.py --commit 506773552eca426ae2182964c42e949459e730dc`

## Computed values

| Table 2 item | Computed value | Source file | Command |
|---|---:|---|---|
| Crosswalk catalog size | 37 | `exports/pipeline/latest/rdamsc_crosswalks.csv` | `git show 506773552eca426ae2182964c42e949459e730dc:exports/pipeline/latest/rdamsc_crosswalks.csv` |
| Outcomes (processed / unreachable / no rules) | 23/11/3 | `exports/pipeline/latest/rdamsc_crosswalks.csv` | `git show 506773552eca426ae2182964c42e949459e730dc:exports/pipeline/latest/rdamsc_crosswalks.csv` |
| Artifact URLs / fetched | 24 / 11 | `exports/pipeline/latest/rdamsc_artifacts.csv` | `git show 506773552eca426ae2182964c42e949459e730dc:exports/pipeline/latest/rdamsc_artifacts.csv` |
| SSSOM files / rows | 26 / 1072 | `exports/sssom/*.sssom.tsv` | `uv run python scripts/make_paper_figures.py --commit 506773552eca426ae2182964c42e949459e730dc` |
| Predicates exact / related / broad / narrow | 844/187/28/13 | `exports/sssom/*.sssom.tsv` | `uv run python scripts/make_paper_figures.py --commit 506773552eca426ae2182964c42e949459e730dc` |
| LLM with rules / without rules | 2/3 | `exports/pipeline/latest/rdamsc_crosswalks.csv` | `git show 506773552eca426ae2182964c42e949459e730dc:exports/pipeline/latest/rdamsc_crosswalks.csv` |
| Deterministic runs | 4 | `exports/pipeline/latest/rdamsc_crosswalks.csv` | `git show 506773552eca426ae2182964c42e949459e730dc:exports/pipeline/latest/rdamsc_crosswalks.csv` |
| Graph nodes / edges | 24/26 | `exports/graph/crosswalk_graph.json` | `git show 506773552eca426ae2182964c42e949459e730dc:exports/graph/crosswalk_graph.json` |
| Benchmark field coverage / value overlap (cases / failures) | 0.3085575396825397 / 0.1673626461988304 (n=1000, failures=not recorded) | `exports/benchmark/datacite_dc_oai_awi_benchmark.json` | `git show 506773552eca426ae2182964c42e949459e730dc:exports/benchmark/datacite_dc_oai_awi_benchmark.json` |

Artifact fetch detail: noaa=5, nasa=3, datacite=3, other=2; failed=13.

## Differences to paper values

| Item | Paper value | Computed | Result |
|---|---:|---:|---|
| Crosswalk catalog size | 37 | 37 | MATCH |
| Outcomes (processed/unreachable/no rules) | 19/11/7 | 23/11/3 | MISMATCH |
| Artifact URLs checked | 45 | 24 | MISMATCH |
| Artifacts fetched | 32 | 11 | MISMATCH |
| SSSOM rows | 993 | 1072 | MISMATCH |
| Predicates exact/related/broad/narrow | 800/152/28/13 | 844/187/28/13 | MISMATCH |
| LLM runs with/without rules | 13/7 | 2/3 | MISMATCH |
| Deterministic runs | 2 | 4 | MISMATCH |
| Graph nodes/edges | 20/23 | 24/26 | MISMATCH |
| Benchmark field coverage/value overlap | 30.9% / 16.7% | 30.9% / 16.7% | MATCH |

## Status/file inconsistencies (reported without correction)

Ready status but no `rdamsc_*.sssom.tsv`: none.

SSSOM file present but status is non-ready: rdamsc_c19, rdamsc_c29.

## Figures

- `paper/figures/fig_pipeline_status_50677355.pdf`
- `paper/figures/fig_pipeline_status_50677355.png`
- `paper/figures/fig_artifact_fetch_50677355.pdf`
- `paper/figures/fig_artifact_fetch_50677355.png`
- `paper/figures/fig_predicates_50677355.pdf`
- `paper/figures/fig_predicates_50677355.png`
- `paper/figures/fig_strategy_50677355.pdf`
- `paper/figures/fig_strategy_50677355.png`
- `paper/figures/fig_benchmark_50677355.pdf`
- `paper/figures/fig_benchmark_50677355.png`
- `paper/figures/fig_overview_50677355.pdf`
- `paper/figures/fig_overview_50677355.png`

Suggested caption attribution: `Data from repository snapshot 50677355 (2026-09-29; full commit 506773552eca426ae2182964c42e949459e730dc).` Figure filenames carry the short commit hash; use this attribution in the manuscript caption when identifying the snapshot.

Source note: all inputs are read-only and read from the selected Git commit using `git show <commit>:<path>` (including `--commit HEAD`). Benchmark failures are shown as 'not recorded' where no matching failures field or `.failures.json` exists.
