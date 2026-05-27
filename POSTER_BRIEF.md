# Conference Poster Brief: m2s3om_graph
## Evidence-Based Metadata Crosswalk Workbench

**Date**: May 27, 2026  
**Project**: m2s3om_graph  
**Source**: Based on MARP presentation at `~/Presentations_Talks/marp-presentations/presentations/Metadata_Crosswalk_Workshop/`

---

## EXECUTIVE SUMMARY

m2s3om_graph is an **evidence-based metadata crosswalk workbench** that automatically extracts, validates, and applies metadata mapping rules from authoritative documentation (PDFs, XSL, HTML). It integrates with the RDA Metadata Standards Catalog (RDAMSC) to provide a production-ready system for metadata conversion across scientific standards.

---

## KEY STATISTICS (Latest Pipeline Results)

### Pipeline Performance
- **37 RDAMSC crosswalks** processed
- **19 crosswalks ready** with authoritative SSSOM output (51.35% success rate)
- **1,280+ mapping rules** extracted across 24 SSSOM files
- **71% artifact fetch success rate** (32/45 documents successfully retrieved)

### Extraction Strategy
- **20 crosswalks** extracted using LLM-assisted parsing (Blablador API)
- **2 crosswalks** extracted using deterministic pattern matching (rdamsc_c36, rdamsc_c38)
- **Average document size**: 59,740 characters (median: 27,129)

### Notable Success Stories
- **rdamsc_c38** (CiteDCAT-AP ↔ DataCite): 160 rules extracted deterministically
- **rdamsc_c36** (EAD ↔ CIDOC CRM): Solved via deterministic extraction
- **datacite44 ↔ dcterms**: 45KB SSSOM file (largest crosswalk)

### Challenge Areas
- **11 crosswalks failed** due to unreachable artifacts (29.73%)
  - Top failing hosts: service.ncddc.noaa.gov, gcmd.nasa.gov, schema.datacite.org
- **7 crosswalks failed parsing** despite successful fetch (18.92%)
  - Complex formats: MARC↔MODS, MIDAS-Heritage↔CIDOC, ISA-TAB↔MAGE-TAB

---

## SYSTEM ARCHITECTURE

### Core Components

1. **RDAMSC Integration Pipeline**
   - API sync with RDA Metadata Standards Catalog
   - Multi-format artifact fetching (PDF, HTML, XSL, XML, RTF, DOC)
   - Document conversion via MarkItDown library

2. **Extraction Engines**
   - **Deterministic Engine**: Pattern matching for table-heavy documents
   - **LLM-Assisted Engine**: Blablador API integration with confidence scoring
   - **Hybrid Strategy**: Fallback from deterministic → LLM → heuristic

3. **SSSOM Export/Import**
   - Authoritative SSSOM TSV format for all mappings
   - Full provenance tracking (git commit, checksums, environment)
   - Round-trip validation (export → import → verify)

4. **Conversion Engine**
   - Intermediate Representation (IR) for format-agnostic processing
   - Parsers: OAI-DC, DataCite, MARCXML, MODS, OpenAIRE
   - Serializers: Dublin Core, DataCite XML
   - Multi-hop routing with automatic reverse rule generation

5. **OAI-PMH Integration**
   - Live metadata harvesting from Helmholtz repositories (DLR, KIT, etc.)
   - Format discovery and automatic bridging (oai_openaire → datacite_xml)
   - Institution-aware configuration

6. **SurrealDB Knowledge Graph**
   - Dual backend: in-memory (fast) + SurrealDB (persistent)
   - 8 tables, 9+ relations, proper indexing
   - Chunk-level provenance with citation anchors

### Technology Stack
- **Language**: Python 3.12+
- **UI**: Streamlit (3 tabs: Browser, Pipeline, Convert)
- **Database**: SurrealDB (graph DB) + in-memory fallback
- **LLM**: Blablador API (compatible with OpenAI format)
- **Package Manager**: uv
- **CI/CD**: Docker, GitLab CI, Makefile automation

---

## STREAMLIT APPLICATION (3 Tabs)

### Tab 1: Crosswalk Browser
- Browse all RDAMSC crosswalks with status indicators
- Filter by mapping type (DIRECT, MISSING, CONDITIONAL, AGGREGATION)
- View rule details (confidence, evidence snippets, semantic loss flags)
- AI-assisted candidate suggestions for incomplete mappings
- Export to SSSOM TSV / JSON / CSV
- Backfill knowledge graph from committed SSSOM files

### Tab 2: Pipeline Orchestration
- Run full RDAMSC bootstrap pipeline
- Single crosswalk ingestion with force re-run
- Live log streaming (300-line display, 2000-line buffer)
- Per-crosswalk status table (msc_id, name, status, reason, timestamp)
- Bootstrap log viewer

### Tab 3: Convert One Record
- **Repository Browser Mode**:
  - Institution selector (Helmholtz network)
  - OAI-PMH metadata format discovery
  - Format bridging display
  - Live record fetching
- **Manual Paste Mode**:
  - Support for OAI-DC, DataCite, MARCXML, MODS
  - Direct SSSOM route conversion
- Route visualization (direct/reverse/transitive)
- Metrics display (applied rules, unmapped fields, semantic loss)
- Pretty-printed XML output with download

---

## TESTING & QUALITY ASSURANCE

- **113 tests passing** (100% pass rate)
- **74% code coverage** overall
- **Execution time**: 2.35 seconds for full test suite
- **100% coverage** on: data models, XML namespaces, SSSOM core, atomic file ops

### Test Categories
- Integration (end-to-end flow)
- RDAMSC pipeline (8 test files)
- Deterministic extraction (3 test files)
- Transform engine (4 test files)
- OAI-PMH integration (4 test files)
- Benchmarking & metrics
- Streamlit UI components

---

## DOCUMENTATION

- **README.md**: Quickstart, Docker setup, CLI commands
- **CODEBASE_WALKTHROUGH.md**: 1,028-line exhaustive architecture guide
- **TALK_RESULTS_SNAPSHOT.md**: Demo-ready statistics and success stories
- **RAG_FUTURE_TODO.md**: Phased roadmap for retrieval-augmented extraction
- **BENCHMARKING.md**: CLI-focused evaluation workflow

---

## COMMITTED OUTPUTS (Reproducible)

### SSSOM Exports (`exports/sssom/`)
- 24 committed SSSOM files
- 1,280 total mapping rules
- Full provenance via `generation_manifest.json` (SHA256 checksums)

### Pipeline Artifacts (`exports/pipeline/latest/`)
- Status JSON (36KB - all crosswalk statuses)
- Statistics summary (success rates, host analysis)
- CSV exports (crosswalks, artifacts)
- Plots (visualizations of pipeline metrics)
- Complete run metadata (git commit, environment, timestamp)

---

## DEMONSTRATION WORKFLOW

### Recommended Demo Story

1. **Start**: Crosswalk Browser → Show rdamsc_c38 (160 rules, deterministic win)
2. **Explain**: Pipeline Tab → Display 51.35% success rate, artifact challenges
3. **Live Demo**: Convert Tab → Fetch OAI-PMH record from DLR
   - Convert `oai_dc` → `datacite_xml` using rdamsc crosswalk
   - Show route visualization (direct/reverse/transitive)
   - Display metrics (applied rules, semantic loss flags)
4. **Highlight**: 71% artifact fetch success, 19 authoritative SSSOM files

### Key Talking Points
- **Evidence-based**: All mappings cite source documents with chunk IDs
- **Production-ready**: 113 passing tests, Docker deployment, CI/CD
- **Standards-compliant**: SSSOM format, OAI-PMH integration, RDAMSC sync
- **Hybrid extraction**: Deterministic + LLM + heuristic fallback
- **Offline-first**: Seeds from committed SSSOM files, no network required for demo

---

## TECHNICAL HIGHLIGHTS FOR POSTER

### Data Flow Diagram (Text Description for Visual)
```
RDAMSC API → Artifact Fetch → Document Conversion (MarkItDown)
    ↓
Deterministic Extraction ← → LLM Extraction (Blablador)
    ↓
Mapping Rules (confidence, citations)
    ↓
SSSOM Export (TSV) → Knowledge Graph (SurrealDB)
    ↓
Conversion Engine (IR + Parsers + Serializers)
    ↓
OAI-PMH Record Transformation
```

### Extraction Strategy Decision Tree
```
1. Try Deterministic Engine (table detection, pattern matching)
   ↓ (if no rules found)
2. Try LLM Engine (Blablador API with structured output)
   ↓ (if API fails)
3. Fallback to Heuristic (low confidence, basic patterns)
```

### SSSOM Format Example
```tsv
subject_id	predicate_id	object_id	mapping_justification	confidence
dc:title	skos:exactMatch	datacite:title	semapv:ManualMappingCuration	0.95
dc:creator	skos:closeMatch	datacite:creator	semapv:ManualMappingCuration	0.85
```

---

## ARTIFACT HOST STATISTICS (For Visual)

### Most Successful Hosts
- www.loc.gov: **9 documents**
- www.cidoc-crm.org: **7 documents**
- github.com: **3 documents**
- www.bgbm.org: **3 documents**

### Most Problematic Hosts
- service.ncddc.noaa.gov: **4 failures**
- gcmd.nasa.gov: **3 failures**
- schema.datacite.org: **3 failures**

### Document Format Distribution
- XSL: 7 | HTML: 5 | PDF: 4 | ZIP: 3 | DOC: 2 | RTF: 2 | Other: 9

---

## FUTURE WORK (RAG Enhancement)

### Planned 4-Phase Roadmap
1. **Phase 1**: Chunk-level retrieval for targeted extraction
2. **Phase 2**: Multi-document grounded Q&A
3. **Phase 3**: Confidence scoring via retrieval quality
4. **Phase 4**: Interactive user feedback loop

---

## CONTACT & RESOURCES

- **Code Repository**: [Add GitLab/GitHub URL]
- **Documentation**: `CODEBASE_WALKTHROUGH.md` (1,028 lines)
- **Test Coverage**: 74% (113/113 tests passing)
- **License**: [Add license]
- **Contact**: Santiago Casas Castro
- **Affiliation**: [Add institution]

---

## POSTER VISUAL SUGGESTIONS

### Layout Recommendations

1. **Top Section**: Title, Authors, Affiliation
2. **Left Column**:
   - Problem Statement (metadata interoperability challenge)
   - System Architecture (component diagram)
   - Technology Stack (badges/icons)
3. **Center Column**:
   - Key Statistics (big numbers with icons)
   - Data Flow Diagram
   - Extraction Strategy Decision Tree
4. **Right Column**:
   - Screenshots (Streamlit 3 tabs)
   - SSSOM Format Example
   - Artifact Host Statistics (bar chart)
5. **Bottom Section**:
   - Demo Workflow (4-step process)
   - Future Work
   - Contact & QR Code

### Color Scheme Suggestions
- **Primary**: Blue (trustworthy, technical)
- **Secondary**: Green (success indicators)
- **Accent**: Orange (warnings, challenges)
- **Neutral**: Gray (structure, text)

### Typography
- **Headers**: Bold, sans-serif (e.g., Helvetica, Arial)
- **Body**: Clean, readable (e.g., Open Sans, Roboto)
- **Code**: Monospace (e.g., Fira Code, Courier)

---

## KEY FILES TO REFERENCE

- `exports/pipeline/latest/rdamsc_stats_summary.json` (all statistics)
- `exports/pipeline/latest/rdamsc_pipeline_status.json` (crosswalk details)
- `exports/sssom/rdamsc_c38.sssom.tsv` (showcase example - 160 rules)
- `exports/sssom/generation_manifest.json` (provenance)
- `TALK_RESULTS_SNAPSHOT.md` (demo script)

---

## INSTRUCTIONS FOR DESIGN AGENT

1. **Use MARP presentation** at `~/Presentations_Talks/marp-presentations/presentations/Metadata_Crosswalk_Workshop/` as starting point
2. **Extract key visuals** from presentation and adapt for poster format
3. **Emphasize statistics**: 51.35% success rate, 1,280 rules, 71% fetch success
4. **Highlight success story**: rdamsc_c38 (160 rules, deterministic extraction)
5. **Include code snippet**: Show SSSOM format or simple mapping example
6. **Add QR code**: Link to live demo or documentation
7. **Keep text minimal**: Use visuals, numbers, and diagrams over paragraphs
8. **Ensure readability**: Test poster at 3-foot, 6-foot, and 10-foot distances

---

**This brief contains all technical details, statistics, and architectural information needed to create a compelling conference poster. The design agent should prioritize visual clarity, key metrics, and the demonstration workflow.**
