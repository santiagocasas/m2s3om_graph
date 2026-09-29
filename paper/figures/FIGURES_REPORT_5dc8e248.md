# Table 2 figure data — 5dc8e248 (2026-03-05)

Commit: `5dc8e24825cb286f1081eb47c6440ead1a8a3500`  
Commit date: `2026-03-05`  
Regeneration: `uv run python scripts/make_paper_figures.py --commit 5dc8e24825cb286f1081eb47c6440ead1a8a3500`

## Computed values

| Table 2 item | Computed value | Source file | Command |
|---|---:|---|---|
| Crosswalk catalog size | 37 | `exports/pipeline/latest/rdamsc_crosswalks.csv` | `git show 5dc8e24825cb286f1081eb47c6440ead1a8a3500:exports/pipeline/latest/rdamsc_crosswalks.csv` |
| Outcomes (processed / unreachable / no rules) | 19/11/7 | `exports/pipeline/latest/rdamsc_crosswalks.csv` | `git show 5dc8e24825cb286f1081eb47c6440ead1a8a3500:exports/pipeline/latest/rdamsc_crosswalks.csv` |
| Artifact URLs / fetched | 45 / 32 | `exports/pipeline/latest/rdamsc_artifacts.csv` | `git show 5dc8e24825cb286f1081eb47c6440ead1a8a3500:exports/pipeline/latest/rdamsc_artifacts.csv` |
| SSSOM files / rows | 18 / 793 | `exports/sssom/*.sssom.tsv` | `uv run python scripts/make_paper_figures.py --commit 5dc8e24825cb286f1081eb47c6440ead1a8a3500` |
| Predicates exact / related / broad / narrow | 625/130/27/11 | `exports/sssom/*.sssom.tsv` | `uv run python scripts/make_paper_figures.py --commit 5dc8e24825cb286f1081eb47c6440ead1a8a3500` |
| LLM with rules / without rules | 13/7 | `exports/pipeline/latest/rdamsc_crosswalks.csv` | `git show 5dc8e24825cb286f1081eb47c6440ead1a8a3500:exports/pipeline/latest/rdamsc_crosswalks.csv` |
| Deterministic runs | 2 | `exports/pipeline/latest/rdamsc_crosswalks.csv` | `git show 5dc8e24825cb286f1081eb47c6440ead1a8a3500:exports/pipeline/latest/rdamsc_crosswalks.csv` |
| Graph nodes / edges | unavailable | `exports/graph/crosswalk_graph.json` | `git show 5dc8e24825cb286f1081eb47c6440ead1a8a3500:exports/graph/crosswalk_graph.json` |
| Benchmark field coverage / value overlap (cases / failures) | unavailable / unavailable (n=unavailable, failures=not recorded) | `unavailable in this snapshot` | `not present in this snapshot` |

Artifact fetch detail: noaa=4, nasa=3, datacite=3, other=3; failed=13.

## Differences to paper values

| Item | Paper value | Computed | Result |
|---|---:|---:|---|
| Crosswalk catalog size | 37 | 37 | MATCH |
| Outcomes (processed/unreachable/no rules) | 19/11/7 | 19/11/7 | MATCH |
| Artifact URLs checked | 45 | 45 | MATCH |
| Artifacts fetched | 32 | 32 | MATCH |
| SSSOM rows | 993 | 793 | MISMATCH |
| Predicates exact/related/broad/narrow | 800/152/28/13 | 625/130/27/11 | MISMATCH |
| LLM runs with/without rules | 13/7 | 13/7 | MATCH |
| Deterministic runs | 2 | 2 | MATCH |
| Graph nodes/edges | 20/23 | unavailable | MISMATCH |
| Benchmark field coverage/value overlap | 30.9% / 16.7% | unavailable | MISMATCH |

## Status/file inconsistencies (reported without correction)

Ready status but no `rdamsc_*.sssom.tsv`: rdamsc_c1, rdamsc_c2.

SSSOM file present but status is non-ready: none.

## Figures

- `paper/figures/fig_pipeline_status_5dc8e248.pdf`
- `paper/figures/fig_pipeline_status_5dc8e248.png`
- `paper/figures/fig_artifact_fetch_5dc8e248.pdf`
- `paper/figures/fig_artifact_fetch_5dc8e248.png`
- `paper/figures/fig_predicates_5dc8e248.pdf`
- `paper/figures/fig_predicates_5dc8e248.png`
- `paper/figures/fig_strategy_5dc8e248.pdf`
- `paper/figures/fig_strategy_5dc8e248.png`
- `paper/figures/fig_overview_5dc8e248.pdf`
- `paper/figures/fig_overview_5dc8e248.png`

Source note: all inputs are read-only and read from the selected Git commit using `git show <commit>:<path>` (including `--commit HEAD`). Benchmark failures are shown as 'not recorded' where no matching failures field or `.failures.json` exists.


## Figure build failures

- fig_benchmark: no AWI benchmark JSON exists in this snapshot
