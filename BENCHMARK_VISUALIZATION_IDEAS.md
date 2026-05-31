# Benchmark Visualization Ideas

## Context

The real live OAI-PMH benchmark now uses `n=1000` distinct AWI records for `oai_openaire` to `oai_dc` conversion.

Measured results:

- Records processed: `1000`
- Fetch/processing failures: `0`
- Field coverage: `30.9%`
- Value overlap: `16.7%`
- Semantic loss rate: `26.4%`

These numbers are lower than the earlier draft values, so the visualization should not frame the result as final conversion quality. A better frame is: **a real-world baseline stress test over heterogeneous records**.

## Communication Goal

Make the graphic feel honest, useful, and positive:

- Emphasize that the benchmark ran at scale on live records.
- Separate operational robustness from semantic fidelity.
- Present low coverage/overlap as diagnostic evidence for targeted refinement, not as a failure.
- Avoid a plain two-bar chart that visually foregrounds only the low percentages.

## Recommended Framing

Title:

**Live OAI-PMH Stress Test**

Subtitle:

**1,000 heterogeneous AWI records converted without fetch failures; benchmark exposes semantic gaps for targeted rule refinement.**

Core message:

**The engine runs reliably at scale; semantic alignment is the next optimization target.**

## Option 1: Dashboard Card

This is the strongest option for a poster.

Layout:

- Large central number: `1,000`
- Label: `live OAI-PMH records benchmarked`
- Three metric tiles below:
  - `100% completed`
  - `30.9% field coverage`
  - `16.7% value overlap`
- Small caption:
  - `Automated baseline over real heterogeneous records; results guide targeted crosswalk refinement.`

Why it works:

- Leads with scale and reliability.
- Keeps lower semantic metrics visible but not visually dominant.
- Looks more like an evidence dashboard than a failure chart.

## Option 2: Pipeline Funnel

Show the benchmark as an operational pipeline:

1. `1,000` records discovered
2. `1,000` records fetched
3. `1,000` records transformed
4. `30.9%` field-level coverage
5. `16.7%` value overlap

Positive angle:

The conversion pipeline works end-to-end on real records. The funnel shows that the bottleneck is semantic matching, not retrieval or execution.

Suggested title:

**From Live Records to Measurable Semantic Gaps**

## Option 3: Robustness vs. Fidelity Split

Use two visual groups:

Operational robustness:

- `1000/1000` completed
- `0` failures
- `100%` benchmark execution success

Semantic fidelity:

- `30.9%` field coverage
- `16.7%` value overlap
- `26.4%` semantic loss rate

Why it works:

- Prevents viewers from interpreting the benchmark as simply “16.7% good.”
- Makes clear that different dimensions are being measured.

Suggested title:

**Reliable Execution, Measurable Semantic Gap**

## Option 4: Baseline-To-Target Graphic

Show the current result as a baseline rather than an endpoint.

Possible visual:

- Current automated baseline: `30.9% field coverage`
- Target after rule refinement: `60-80%`
- Human-curated reference ceiling: future work / unknown

Positive angle:

The benchmark creates a measurable starting point for iterative improvement.

Use this only if target ranges are clearly labeled as aspirational, not measured.

## Option 5: Diagnostic Heatmap

Create a compact matrix of benchmark dimensions:

| Dimension | Result | Interpretation |
| --- | ---: | --- |
| Fetch success | `100%` | Strong |
| Transform execution | `100%` | Strong |
| Field coverage | `30.9%` | Needs rule refinement |
| Value overlap | `16.7%` | Needs normalization and semantic alignment |
| Semantic loss tracking | Available | Diagnostic transparency |

Positive angle:

This presents the system as an evaluable, transparent pipeline.

## Suggested Poster Copy

Short version:

> Live benchmark over 1,000 AWI OAI-PMH records completed without fetch failures. Field coverage and value overlap expose the next target: refining crosswalk rules and normalization for heterogeneous real-world metadata.

Very short version:

> 1,000 live records processed; semantic gaps are now measurable and targetable.

## Recommended Design Direction

Use the dashboard-card version for the poster:

- Big `1,000` in the center.
- HMC dark blue for main text.
- HMC health and matter colors for semantic metrics.
- HMC mint/green or AST color for the `100% completed` tile.
- White background.
- Minimal axis/grid usage.
- Avoid making the low percentages the largest visual marks.

## Source Files

Current benchmark code and output:

- `scripts/run_datacite_dc_benchmark.py`
- `exports/benchmark/datacite_dc_oai_awi_benchmark.json`
- `exports/benchmark/datacite_dc_oai_awi_benchmark.csv`
- `plots/datacite_dublincore_benchmark_bar.py`
- `poster_datacite_dublincore_benchmark_bar.png`
