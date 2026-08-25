# m2s3om_graph

## What This Is

A metadata standards mapping tool that ingests PDF documents with mapping rules, extracts structured mapping definitions, and applies those rules to transform metadata records. It provides transitive mapping across multiple standards with semantic loss tracking, plus a Vite+FastAPI web application with a Convert-a-record page, and GitLab Pages for static browsing.

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

**Shipped:** 2026-08-25 (v2.0 Deployment Surfaces)

### What Was Built

- Phase 02: Exported real SSSOM TSV data to JSON for GitLab Pages static explorer
- Phase 03: Wired suggestion API to existing Blablador client for candidate mapping generation
- Phase 04: Added browser-memory curation with TSV export workflow
- Phase 05: Unified Vite+FastAPI app with Convert-a-record page, multi-stage Docker packaging

## Requirements

### Validated

- ✓ PDF ingestion with rule extraction — existing
- ✓ Structured mapping record definitions — existing
- ✓ Rule application engine — existing
- ✓ Graph-based transitive mapping — existing
- ✓ Semantic loss tracking — existing
- ✓ Streamlit visualization UI — existing
- ✓ Project rename from kaigraph to m2s3om_graph — Phase 01
- ✓ SSSOM→JSON export for static explorer — Phase 02
- ✓ Vite explorer integrated into canonical Pages source — Phase 02
- ✓ Suggestion API wired to Blablador client — Phase 03
- ✓ Mocked-LLM test coverage for `/health` and `/suggest` — Phase 03
- ✓ Browser-memory curation with TSV export — Phase 04
- ✓ Unified Vite+FastAPI Hugging Face Space app — Phase 05
- ✓ Multi-stage Docker packaging with StaticFiles serving — Phase 05

### Active

- [ ] Unified Explorer — Graph + Stats Pages — New milestone: Bring existing GitLab Pages content (Cytoscape graph + pipeline stats/plots) into the Vite+FastAPI app as new routes (/graph, /stats)

### Out of Scope

- [Value transformation] — mappings are field-level only, no content modification
- [Real-time processing] — batch-oriented ingestion and transformation
- [Multi-user collaboration] — single-user analysis tool
- [Full metadata validation] — focuses on mapping rules, not schema compliance

## Context

**Technical Environment:**
- Python 3.12+ runtime with `uv` package manager
- SurrealDB as graph database for mapping relationships (Streamlit internal only)
- Vite + FastAPI for main web application
- Streamlit for internal visualization (not packaged in production)
- Existing codebase has mature PDF ingestion and rule application logic

**Domain:**
- Metadata standards mapping (DataCite ↔ Dublin Core ↔ others)
- Semantic interoperability between research data ecosystems
- Academic/library metadata transformation workflows

**Known Issues:**
- `claude_suggestions/` contains the original suggestion-API scaffold copy on disk; logic was promoted into `server/`. Whether this scaffold directory should be removed/deprecated is not yet resolved.
- `spaces/m2s3om-streamlit-space/{Dockerfile,README.md}` were re-added as "deployment templates" after the original scaffold was reverted; not yet disambiguated whether these are intentional reference templates or leftover scope creep.
- CI workflows `aiprov-build.yml`, `aiprov-promote.yml`, and `aiprov-release.yml` reference `scripts/provlog.py`, `scripts/build_dashboard.py`, and `scripts/requirements.txt` that don't exist in the repo.

**Constraints:**
- Tech Stack: Python 3.12+ with uv — consistency with existing build system
- Data Formats: XML/JSON only (field-level mapping, no value transformation)
- Visualization: sigma.js integration (existing tool, no replacement) for Streamlit; Vite explorer uses Cytoscape.js
- Semantic Tracking: Must preserve evidence/chains for transitive mappings

**Key Decisions:**

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Field-level only mappings | Value transformation too complex; focus on structural alignment | ✓ Good |
| Graph-based transitive mapping | Enables multi-hop relationships between standards | ✓ Good |
| Semantic loss tracking | Critical for assessing mapping quality and reliability | ✓ Good |
| Rename kaigraph → m2s3om_graph | Consistent project naming across codebase | ✓ Good |
| Integrate scaffolds instead of replacing existing code | Existing pipeline, Streamlit app, Blablador client, and Pages setup remain authoritative where they overlap | — Pending |
| Re-scope Phase 05 from Streamlit Space to unified Vite+FastAPI app | User feedback indicated need for production-grade web app instead of Streamlit prototype | ✓ Good — shipped 2026-08-17 |
| Keep GitLab Pages as static browse-only mirror | Static explorer remains separate from dynamic Vite+FastAPI app | ✓ Good |

---

*Last updated: 2026-08-25 after completing milestone v2.0 Deployment Surfaces*

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
5. Add shipped features to Validated section
