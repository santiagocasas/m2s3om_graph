# m2s3om_graph

## What This Is

A metadata standards mapping tool that ingests PDF documents with mapping rules, extracts structured mapping definitions, and applies those rules to transform metadata records. It provides transitive mapping across multiple standards with semantic loss tracking, plus a Streamlit-based UI for visualization and interactive exploration.

## Core Value

Enable cross-walking between metadata standards (DataCite, Dublin Core, etc.) by providing machine-readable mapping rules that can be applied automatically while tracking where information is lost in translation.

## Current Milestone: v2.0 Deployment Surfaces

**Goal:** Integrate the reference deployment and curation scaffolds into the existing codebase without creating parallel implementations.

**Target features:**
- Export committed SSSOM TSV files and the standards list into the static crosswalk explorer JSON shape.
- Integrate the Vite GitLab Pages explorer into the canonical Pages source with exactly one `pages` CI job.
- Wire the FastAPI suggestion API to the existing Blablador client used by the extraction pipeline.
- Add browser-memory curation for candidate mappings, including `accepted_candidates.tsv` export.
- Package the existing Streamlit app into the Hugging Face Space scaffold with environment-based configuration.

## Requirements

### Validated

- ✓ PDF ingestion with rule extraction — existing
- ✓ Structured mapping record definitions — existing
- ✓ Rule application engine — existing
- ✓ Graph-based transitive mapping — existing
- ✓ Semantic loss tracking — existing
- ✓ Streamlit visualization UI — existing
- ✓ Project rename from kaigraph to m2s3om_graph — Phase 01

### Active

- [ ] Export committed SSSOM TSV files and standards into static-site JSON — GitLab Pages data source
- [ ] Integrate static crosswalk explorer into the canonical Pages site — deployment surface
- [ ] Wire suggestion API scaffold to the existing Blablador client — candidate mapping generation
- [ ] Add browser-only curation decisions and TSV export — manual merge workflow
- [ ] Package Streamlit app for Hugging Face Spaces — environment-based deployment

### Out of Scope

- [Value transformation] — mappings are field-level only, no content modification
- [Real-time processing] — batch-oriented ingestion and transformation
- [Multi-user collaboration] — single-user analysis tool
- [Full metadata validation] — focuses on mapping rules, not schema compliance

## Context

**Technical Environment:**
- Python 3.12+ runtime with `uv` package manager
- SurrealDB as graph database for mapping relationships
- Streamlit for web-based UI with sigma.js for graph visualization
- Existing codebase has mature PDF ingestion and rule application logic

**Domain:**
- Metadata standards mapping (DataCite ↔ Dublin Core ↔ others)
- Semantic interoperability between research data ecosystems
- Academic/library metadata transformation workflows

**Known Issues:**
- Documentation may not reflect current feature set
- Need more sample PDFs to demonstrate capability
- Deployment scaffolds in `claude_suggestions/` are reference material and are not yet wired into the repo

## Constraints

- **Tech Stack**: Python 3.12+ with uv — consistency with existing build system
- **Data Formats**: XML/JSON only (field-level mapping, no value transformation)
- **Visualization**: sigma.js integration (existing tool, no replacement)
- **Semantic Tracking**: Must preserve evidence/chains for transitive mappings

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Field-level only mappings | Value transformation too complex; focus on structural alignment | ✓ Good |
| Graph-based transitive mapping | Enables multi-hop relationships between standards | ✓ Good |
| Semantic loss tracking | Critical for assessing mapping quality and reliability | ✓ Good |
| Rename kaigraph → m2s3om_graph | Consistent project naming across codebase | ✓ Good |
| Integrate scaffolds instead of replacing existing code | Existing pipeline, Streamlit app, Blablador client, and Pages setup remain authoritative where they overlap | — Pending |

---
*Last updated: 2026-06-17 after starting milestone v2.0 Deployment Surfaces*

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state
