# Kaigraph Codebase: Complete Linear Walkthrough

**Date**: March 2026  
**Project**: kaigraph - Evidence-based metadata crosswalk workbench  
**Language**: Python 3.12+  
**Runtime**: uv + Streamlit + SurrealDB

---

## Table of Contents

1. [Entry Points & Initialization](#1-entry-points--initialization)
2. [Data Models & Persistence Layer](#2-data-models--persistence-layer)
3. [RDAMSC Sync Pipeline](#3-rdamsc-sync-pipeline)
4. [Deterministic Extraction Engine](#4-deterministic-extraction-engine)
5. [LLM-Assisted Extraction](#5-llm-assisted-extraction)
6. [Transform & Conversion Engine](#6-transform--conversion-engine)
7. [Benchmark & Comparison](#7-benchmark--comparison)
8. [SSSOM Export & Round-trip](#8-sssom-export--round-trip)
9. [Streamlit UI Flow](#9-streamlit-ui-flow)
10. [Orchestration & Config](#10-orchestration--config)
11. [End-to-End Execution Flow](#11-end-to-end-execution-flow)

---

## 1. Entry Points & Initialization

### CLI Entry Point

**File**: `src/kaigraph/cli/main.py`

The CLI provides the following commands:

| Command | Purpose |
|---------|---------|
| `ingest-pdf` | Ingest a PDF containing mapping rules (default: DataCite↔DC) |
| `sync-rdamsc` | Fetch catalog from RDA Metadata Standards Catalog API |
| `ingest-rdamsc` | Extract mapping rules from crosswalk documentation |
| `bootstrap-rdamsc` | Full pipeline: sync + ingest + SSSOM export |
| `demo-convert` | Fast synthetic conversion demo |
| `benchmark-fixture` | Run fixture benchmark and output JSON |

Each command uses `build_default_store()` to instantiate either:
- **InMemoryCrosswalkStore**: In-process key-value (default)
- **SurrealCrosswalkStore**: Persistent SurrealDB instance (if `KAIGRAPH_USE_SURREAL=1`)

### Streamlit App

**File**: `app/app.py`

Launches a web UI with 4 tabs and a sidebar:

| Tab | Location | Purpose |
|-----|----------|---------|
| **Crosswalks** | `app/views/crosswalks.py` | Browse & inspect RDAMSC mappings, generate SSSOM, export rules |
| **Pipeline** | `app/views/pipeline.py` | Run batch ingestion with live logs |
| **Convert** | `app/views/transform.py` | Single-record demo with OAI-PMH fetch or manual paste |

**Session Management**: `app/state.py`
- `get_store()`: Lazy-loads CrosswalkStore into Streamlit session
- `sssom_dir()`: Ensures SSSOM export directory exists
- `ensure_seeded()`: seeds the app from committed SSSOM exports first and skips remote RDAMSC catalog sync unless `KAIGRAPH_AUTO_SYNC_ON_START=1`

**Sidebar**: `app/views/system.py`
- Displays runtime config (DB URL, Blablador API key status)
- Model selector for LLM (Blablador) is lazy-loaded so startup does not block on remote model discovery

---

## 2. Data Models & Persistence Layer

### High-Level Models

**File**: `src/kaigraph/models/`

```python
# standards.py
Standard(id, name, version, source_url, description)
Element(id, standard_id, path, label, scope_note, constraints)
Definition(id, element_id, text)
Example(id, element_id, text)
Chunk(id, standard_id, element_id?, content, source_url, anchor, embedding)
Constraint(kind: ConstraintType, value)

# crosswalk.py
Crosswalk(id, source_standard_id, target_standard_id, created_at, agent_version)
MappingRecord(
    id, crosswalk_id,
    source_element_id, target_element_id,
    confidence: [0.0, 1.0],
    justification, transformation_hint,
    ambiguity_flag, semantic_loss_flag,
    citations: [Citation],
    status: MappingStatus
)
Citation(chunk_id, url?, anchor?, snippet)
```

### Database Models

**File**: `src/kaigraph/db/models.py`

```python
StandardRecord(
    id, name, namespace?, version?,
    urls: Dict[str, str],         # e.g., {"api": "...", "spec": "..."}
    external_ids: Dict[str, str]  # e.g., {"msc_id": "msc:c5"}
)

ElementRecord(
    id, standard_id, path, label,
    full_iri?, notes?,
    parent_element_id?
)

CrosswalkRecord(
    id, name,
    source_standard_id, target_standard_id,
    version?, doi?, msc_id?, doc_uri?,
    created_at: datetime
)

MappingRuleRecord(
    id, crosswalk_id,
    source_element_id?, source_paths: [str],
    target_element_id?, target_paths: [str],
    mapping_type: MappingType,
    confidence: [0.0, 1.0],
    semantic_loss: bool,
    ambiguity: bool,
    transform: Dict,
    notes?: str,
    evidence: [EvidenceRecord]
)

# MappingType enum: DIRECT, MISSING, CONDITIONAL, AGGREGATION, DECOMPOSITION, PASSTHROUGH

ArtifactDocumentRecord(
    id, crosswalk_id,
    source_url, resolved_url,
    content_type, extension,
    markdown: str,
    status, fetched_at
)

ArtifactChunkRecord(
    id, document_id, crosswalk_id,
    ordinal: int,
    text: str
)

EvidenceRecord(
    id, mapping_rule_id,
    source, doc_uri, page_number,
    row_id, snippet,
    bbox?, chunk_id?
)

CrosswalkBundle(
    crosswalk: CrosswalkRecord,
    source_standard: StandardRecord,
    target_standard: StandardRecord,
    rules: [MappingRuleRecord]
)
```

### Storage Backends

**File**: `src/kaigraph/db/crosswalk_repository.py`

Both backends implement the `CrosswalkStore` interface:

```python
class CrosswalkStore:
    def apply_schema() -> None
    def upsert_standard(standard: StandardRecord) -> StandardRecord
    def upsert_element(element: ElementRecord) -> ElementRecord
    def upsert_crosswalk(crosswalk: CrosswalkRecord) -> CrosswalkRecord
    def upsert_mapping_rule(rule: MappingRuleRecord) -> MappingRuleRecord
    def upsert_evidence(evidence: EvidenceRecord) -> EvidenceRecord
    def upsert_artifact_document(doc: ArtifactDocumentRecord) -> ArtifactDocumentRecord
    def upsert_artifact_chunk(chunk: ArtifactChunkRecord) -> ArtifactChunkRecord
    def list_crosswalks() -> [CrosswalkRecord]
    def list_standards() -> [StandardRecord]
    def list_elements(standard_id: str) -> [ElementRecord]
    def list_artifact_documents(crosswalk_id: str) -> [ArtifactDocumentRecord]
    def list_artifact_chunks(crosswalk_id: str) -> [ArtifactChunkRecord]
    def get_crosswalk_bundle(crosswalk_id: str) -> CrosswalkBundle?
```

**InMemoryCrosswalkStore**: Python dicts with defaultdicts for indexes
**SurrealCrosswalkStore**: WebSocket connection to SurrealDB with SurrealQL queries

### SurrealDB Schema

**File**: `src/kaigraph/db/surreal_schema.py`

8 tables:
- `standard`, `element`, `crosswalk`, `mapping_rule`, `evidence`
- `artifact_document`, `artifact_chunk`, `ir_record`

9 relation tables:
- `standard_has_element`, `crosswalk_maps_from`, `crosswalk_maps_to`
- `crosswalk_has_rule`, `rule_has_evidence`, `crosswalk_has_artifact`
- `artifact_has_chunk`, `element_parent_of`, `benchmark_has_result`

Indexes on frequently-queried fields:
- `(standard.name, standard.version)` UNIQUE
- `(element.standard_id, element.path)` UNIQUE
- `(crosswalk.source_standard_id, crosswalk.target_standard_id, crosswalk.version)` UNIQUE
- `mapping_rule.crosswalk_id`, `mapping_rule.mapping_type`
- `evidence.mapping_rule_id`, `evidence.(page_number, row_id)`

---

## 3. RDAMSC Sync Pipeline

### Step 1: Sync Catalog

**Files**: `src/kaigraph/rdamsc/api.py`, `ingest.py:sync_rdamsc_catalog()`

```
RDAMSCClient.list_mappings()
  ↓ (paginated API calls)
  ├─ Extract source & target standard entities
  ├─ For each valid pair:
  │   ├─ _standard_from_entity(entity) → StandardRecord
  │   │   └─ Extract name, version, URLs, external IDs
  │   └─ Create CrosswalkRecord
  └─ Persist to store
```

**Key Functions**:
- `RDAMSCClient._get_json(path)`: HTTP GET to RDAMSC API with 30s timeout
- `_standard_from_entity()`: Extract StandardRecord from RDAMSC response
- `_source_target_entities()`: Find input/output scheme entities in response
- `_primary_doc_uri()`: Select best documentation URL (prefer .pdf > .html > others)

**Output**: Count of CrosswalkRecords inserted

### Step 2: Fetch Artifacts

**File**: `src/kaigraph/rdamsc/artifacts.py`

Converts documentation (PDF, HTML, TXT, XML, XSL) into normalized markdown text.

```
fetch_artifact_text(url)
  ├─ _candidate_urls(url)  # Generate fallback URLs (GitHub raw, http→https)
  ├─ for each candidate_url:
  │   ├─ requests.get(url, headers=DEFAULT_HEADERS)
  │   ├─ Try MarkItDown conversion first
  │   ├─ If fails, check content-type & path:
  │   │   ├─ PDF → _extract_pdf_text() via pypdf
  │   │   ├─ HTML → _extract_html_text() via HTMLParser
  │   │   ├─ .doc → _convert_legacy_doc_via_soffice() (LibreOffice)
  │   │   └─ Text-like → plain text normalization
  │   └─ Return ArtifactText(url, content_type, markdown)
  └─ else: raise ArtifactFetchError
```

**Normalizations**:
- `_normalize_text()`: Collapse 3+ newlines, strip
- `_normalize_legacy_shifted_text()`: Handle PDFs with garbled character encodings
- Max output: 200,000 characters per artifact

**Output**: `ArtifactText(url, content_type, text)`

### Step 3: Persist in Knowledge Graph

**Function**: `_persist_artifacts_in_kg(store, crosswalk, artifacts)`

```
For each artifact:
  ├─ Create ArtifactDocumentRecord
  │   └─ markdown = full text
  ├─ Chunk markdown:
  │   ├─ _chunk_markdown(text, chunk_chars=3200, overlap_chars=320)
  │   └─ For each chunk: ArtifactChunkRecord(ordinal, text)
  └─ Upsert all records to store
```

Returns: (document_count, chunk_count)

### Step 4: Extract Mapping Rules (Strategy Selection)

**Function**: `ingest_rdamsc_crosswalk_docs()`

Selects extraction strategy based on artifact URL:

| Strategy | Condition | Extractor |
|----------|-----------|-----------|
| **deterministic_pdf** | URL contains "datacite_dublincore_mapping.pdf" | `parse_mapping_pdf()` (regex-based table parsing) |
| **deterministic_html_loc** | URL contains "loc.gov/marc/dccross" | `_ingest_loc_dccross_html()` (MARC field pattern) |
| **deterministic_generic** | ≥8 rules found by generic engine | `extract_deterministic_candidates()` + optional LLM |
| **llm** (fallback) | < 8 rules or no deterministic match | Blablador API extraction |

**Merged Artifact Processing**:
- Combine all artifact markdown (max 140K chars)
- `_merged_markdown_from_kg()`: Concatenate artifact chunks with headers

**Rule Persistence**:
- `_ingest_candidate_records()`: For each candidate {source_path, target_path, ...}
  - Create ElementRecord if not exists
  - Create MappingRuleRecord
  - Create EvidenceRecord linking rule to source doc

**Deduplication**: Track `seen_pairs: Set[(source.lower(), target.lower())]`

---

## 4. Deterministic Extraction Engine

### Architecture

**Files**: `src/kaigraph/ingest/deterministic/`

```
normalize_text_for_deterministic(text)
  ↓ (clean RTF, control words, normalize whitespace)
extract_deterministic_candidates(text, max_rules=160)
  ├─ Run extractors:
  │   ├─ extract_assignment_candidates() → assignment patterns
  │   └─ extract_markdown_table_candidates() → markdown tables
  ├─ Deduplicate by (source.lower(), target.lower(), type)
  └─ Return up to 160 candidates + diagnostics
```

### Extractors

#### Assignment Pattern Extractor

**Regex**: `^(?P<src>[A-Za-z][A-Za-z0-9_.:@/\-]{0,80})\s*(?P<op>=|->|=>)\s*(?P<tgt>.+)$`

Matches lines like:
```
titleproper = E35_Title
unitdate@normal -> dcterms:issued
```

**Validation**:
- `_looks_like_source()`: Non-whitespace identifier (alphanumeric + `_.:@/-`)
- `_looks_like_target()`: Contains `:` or `.` or CIDOC `E\d+` or UPPERCASE term

**Mapping Type Detection**:
- "not present" → MISSING
- "concatenate" or "is composed of" → AGGREGATION
- "(join)" or "has" with `:` → DECOMPOSITION
- `@` in source → CONDITIONAL
- else → DIRECT

**Confidence**: 0.9 (DIRECT/MISSING), 0.84 (DECOMPOSITION), 0.82 (AGGREGATION), 0.8 (else)

#### Markdown Table Extractor

**Pattern**: Lines starting with `|`

Splits on `|` and takes first two columns as source/target.

**Mapping Type**: DIRECT (default), CONDITIONAL if `@` in source

**Confidence**: 0.78

### Normalizer

**File**: `normalizers.py`

```python
normalize_text_for_deterministic(text):
  1. CRLF → LF
  2. RTF hex escapes (\' sequences) → space
  3. RTF control words (\word) → space
  4. Unicode dashes (–—‐‑) → ASCII `-`
  5. Unicode arrow (→) → `->`
  6. Collapse whitespace to single spaces
  7. Return only non-empty lines
```

### Diagnostics

```python
@dataclass
class DeterministicDiagnostics:
    total_chars, normalized_chars, total_lines
    extractor_counts: Dict[str, int]  # {"assignment": 45, "markdown_table": 12}
    candidates_before_dedupe: int
    candidates_after_dedupe: int
```

---

## 5. LLM-Assisted Extraction

### Architecture

**Files**: `src/kaigraph/candidates/blablador.py`, `rdamsc/llm_extract.py`

```
extract_mapping_candidates_with_meta(merged_markdown, source_std_name, target_std_name)
  ├─ if BLABLADOR_API_KEY set:
  │   └─ Call Blablador API (OpenAI-compatible)
  └─ else:
      └─ Fallback: suggest_candidate_mappings() (heuristic)
```

### Blablador Integration

**Prompt**:
```
Extract field mapping rules from the following documentation:
[merged_markdown]

Source standard: {source_std_name}
Target standard: {target_std_name}

For each rule, return JSON:
{
  "source_path": "field_name",
  "target_path": "target_field",
  "mapping_type": "direct|missing|conditional|aggregation",
  "confidence": 0.0-1.0,
  "evidence": "snippet from docs",
  "notes": "explanation"
}
```

**Config**:
- Model: Read from `KAIGRAPH_LLM_MODEL` (default: "alias-fast")
- API base: `BLABLADOR_BASE_URL` (default: Helmholtz Blablador)
- Timeout: 120 seconds per request

**Error Handling**:
- If API fails: return empty diagnostics dict with `llm_error`
- If parsing fails: skip malformed entries

### Heuristic Fallback

**Function**: `suggest_candidate_mappings(source_text, target_paths, max_candidates=2)`

Simple TF-IDF-like scoring:
- Score each target by word overlap with source
- Confidence = 0.79 * (overlap_ratio)
- Return top-k candidates

---

## 6. Transform & Conversion Engine

### Intermediate Representation (IR)

**File**: `src/kaigraph/transform/ir.py`

```python
@dataclass
class IRValue:
    text: str
    field: str = ""
    context_data: Dict[str, Any] = field(default_factory=dict)
    
    # Alias setters for different metadata formats
    def set_datacite_value(field: str, value: str) -> None
    def set_dcterms_value(field: str, value: str) -> None

# Internal format is always:
IR = Dict[str, List[IRValue]]
# Example:
# {
#   "dcterms:title": [IRValue(text="Example Title")],
#   "dcterms:creator": [IRValue(text="Smith, Alice"), IRValue(text="Jones, Bob")]
# }
```

### Parsers

**File**: `transform/parsers.py`

Converts source metadata formats → IR:

| Parser | Input | Output |
|--------|-------|--------|
| `parse_oai_dc_xml_to_ir()` | OAI Dublin Core XML | IR with dcterms:* keys |
| `parse_datacite_xml_to_ir()` | DataCite XML | IR with datacite:* keys |
| `parse_openaire_xml_to_ir()` | OpenAIRE XML | IR with mixed keys |
| `parse_dc_export_text_to_ir()` | Plain text (`field: value`) | IR |

**Field Aliasing**:
- Common aliases normalized (e.g., `publicationYear` → `datacite:publicationYear`)
- Multi-valued fields split on `|` or `;`

### Rule Application

**File**: `transform/apply.py`

```python
apply_mapping_rules(source_ir: IR, rules: [MappingRuleRecord]) 
  → (target_ir: IR, report: ApplyReport)
```

**Algorithm**:
```
For each source_path in source_ir.keys():
  ├─ Find matching rules where rule.source_paths contains source_path
  ├─ For each matching rule:
  │   ├─ Apply rule.transform operation:
  │   │   ├─ "copy" → copy values to target_paths
  │   │   ├─ "drop" → skip (MISSING type)
  │   │   ├─ "value_map" → lookup source value in mapping dict
  │   │   ├─ "concat" → join multiple source values
  │   │   └─ "split" → split value into multiple targets
  │   ├─ Create IRValue entries in target_ir[target_path]
  │   └─ Track rule_id in applied_rule_ids
  └─ else:
      └─ Add source_path to unmapped_fields

Report contains:
  - applied_rule_ids: [str]
  - unmapped_fields: [str]
  - semantic_loss_rules: [str]  # rules with semantic_loss=True
  - ambiguous_rules: [str]       # rules with ambiguity=True
```

### Serializers

**File**: `transform/serializers.py`

Converts IR → target metadata formats:

| Serializer | Output | Usage |
|------------|--------|-------|
| `ir_to_dublin_core_xml()` | OAI Dublin Core XML | `<rdf:RDF>` with `dc:` and `dcterms:` elements |
| `ir_to_datacite_xml()` | DataCite XML | `<resource>` with DataCite schema |

**Field Mapping** (example for DataCite):
- `dcterms:title` → `<titles><title>...</title></titles>`
- `dcterms:creator` → `<creators><creator><creatorName>...</creatorName></creator></creators>`
- `dcterms:issued` → `<publicationYear>...</publicationYear>`

---

## 7. Benchmark & Comparison

### Metrics

**File**: `src/kaigraph/benchmark/metrics.py`

```python
compare_ir(actual: IR, expected: IR) 
  → (field_coverage: float, value_overlap: float, metrics: [FieldMetric])

compare_ir_detailed(
    actual: IR, expected: IR,
    semantic_loss_rules: int, total_rules: int
) → (metrics, diffs, confusion_matrix)
```

**Metrics Calculation**:

**Field Coverage** = `|fields_in_actual ∩ fields_in_expected| / |fields_in_expected|`

**Value Overlap** (Jaccard) = `|actual_values ∩ expected_values| / |actual_values ∪ expected_values|`

**Per-Field Confusion Matrix**:
```
For each field in expected:
  ├─ TP (True Positive): value in both actual & expected
  ├─ FP (False Positive): value in actual but not expected
  ├─ FN (False Negative): value in expected but not actual
  └─ normalized_overlap = TP / (TP + FP + FN)
```

**Semantic Loss Rate** = `semantic_loss_rule_count / total_rule_count`

### Runner

**File**: `benchmark/runner.py`

```python
run_elib_benchmark(bundle: CrosswalkBundle, record_ids: [str])
  → BenchmarkSummary

run_fixture_benchmark(bundle, source_xml, expected_text, n_cases=1)
  → BenchmarkSummary
```

**For each record**:
1. Parse source metadata (fetch from eLib or provided XML)
2. Parse expected metadata (from provided text)
3. `apply_mapping_rules(source_ir, bundle.rules)` → converted_ir
4. `compare_ir(converted_ir, expected_ir)` → metrics
5. Track BenchmarkCase(case_id, direction, metrics, diffs, confusion_matrix)

**Summary**:
```python
@dataclass
class BenchmarkSummary:
    cases: [BenchmarkCase]
    avg_field_coverage: float
    avg_value_overlap: float
    avg_semantic_loss_rate: float
```

### Report

**File**: `benchmark/report.py`

Export functions:
- `benchmark_summary_to_json(summary)` → JSON with aggregate + per-case metrics
- `benchmark_summary_to_csv(summary)` → CSV rows for spreadsheet analysis

---

## 8. SSSOM Export & Round-trip

### Standard for Sharing Ontology Mappings (SSSOM)

**File**: `src/kaigraph/sssom.py`

SSSOM is a TSV-based format for mapping sets. Kaigraph uses it as authoritative export/import.

#### Export: CrosswalkBundle → SSSOM TSV

**File Structure**:
```
# mapping_set_id: kaigraph:rdamsc_c5
# mapping_set_version: 1.0
# mapping_set_description: RDA to Dublin Core (source -> target)
# curie_map:
#   src: https://kaigraph.local/source_standard_id/
#   dst: https://kaigraph.local/target_standard_id/
#   skos: http://www.w3.org/2004/02/skos/core#
#   semapv: https://w3id.org/semapv/vocab/

record_id	subject_id	subject_label	predicate_id	object_id	object_label	mapping_justification	confidence	comment
rule_id_1	src:title	source_field	skos:exactMatch	dst:title	target_field	semapv:ManualMappingCuration	0.95	{"mapping_type":"direct","source_paths":[...],"target_paths":[...],"transform":{...},"semantic_loss":false,"ambiguity":false,"notes":null}
```

**Predicate Assignment**:
- DIRECT → `skos:exactMatch`
- MISSING → `skos:relatedMatch`
- CONDITIONAL → `skos:relatedMatch`
- AGGREGATION → `skos:broadMatch`
- DECOMPOSITION → `skos:narrowMatch`

**Justification**:
- Ambiguity flag → `semapv:CompositeMatching`
- MISSING type → `semapv:ManualMappingCuration`
- Default → `semapv:ManualMappingCuration`

#### Import: SSSOM TSV → MappingRuleRecord List

**Function**: `sssom_tsv_to_rules(content: str, crosswalk_id: str) → [MappingRuleRecord]`

Parse TSV header (YAML) + data rows:
1. Extract metadata (mapping_set_id, curie_map)
2. For each data row:
   - Parse comment JSON to recover full rule payload
   - Reconstruct MappingRuleRecord with source_paths, target_paths, mapping_type, etc.
   - Handle missing fields by inferring from labels/predicates

---

## 9. Streamlit UI Flow

### Tab 1: Crosswalks (Browse & Inspect)

**File**: `app/views/crosswalks.py`

**Workflow**:
```
1. [Maintenance] Refresh RDAMSC catalog (optional)
2. Select a crosswalk from dropdown
3. [Maintenance] Generate missing SSSOM for all OR force re-ingest selected
4. View summary: source → target, MSC ID, DOI, pipeline status
5. View rules (with filtering by mapping type + search by field name)
6. For each rule: expand to see confidence, flags, evidence, snippets
7. [Advanced] Suggest AI candidate mappings
8. Export: SSSOM TSV / rules JSON / rules CSV
```

**Key Functions**:
- `_status_code(crosswalk, status_map)` → resolve status (ready/kg_out_of_sync/missing_sssom/failed_*)
- `_ingest_selected(crosswalk, force=False)` → run `ingest_rdamsc_crosswalk_docs()`
- `_ingest_all(force=False)` → batch ingest all crosswalks
- `load_sssom_rules(path, crosswalk_id)` → read SSSOM TSV as MappingRuleRecord list
- `backfill_kg_from_sssom()` → if KG is stale but SSSOM exists, load rules from SSSOM

**Status Labels**:
- `ready`: SSSOM written, rules in KG
- `kg_out_of_sync`: SSSOM exists but KG rules missing
- `missing_sssom`: Ingestion succeeded but no rules extracted
- `failed_unreachable`: Artifacts could not be fetched
- `failed_unsupported`: Artifacts fetched but conversion failed
- `failed_parse`: Extraction failed

### Tab 2: Pipeline (Run Batch Ingestion)

**File**: `app/views/pipeline.py`

**Workflow**:
```
1. Select a mapping (for single-run) or run full pipeline
2. Click "Run full pipeline" / "Run selected" / "Force re-run"
3. Live log output (streaming updates)
4. Display JSON result from pipeline run
5. Table of per-crosswalk status (msc_id, name, status label, reason, updated_at)
6. View status file path & bootstrap log
```

**Key Functions**:
- `run_bootstrap_pipeline(store, sssom_dir, force, only_crosswalk_id, logger)` → orchestrate full pipeline
- Session state tracking: `pipeline_logs`, `pipeline_last_result`

### Tab 3: Convert One Record

**File**: `app/views/transform.py`

**Workflow - OAI-PMH Fetch Mode**:
```
1. Enter OAI-PMH base URL (default: eLib)
2. Enter record identifier (default: eLib example)
3. [Optional] Click "Discover metadata formats" (calls OAI ListMetadataFormats)
4. Select source metadataPrefix (dropdown)
5. Click "Fetch source record"
6. Pick the target format
7. Convert through the authoritative SSSOM route
```

**Workflow - Manual Paste Mode**:
```
1. Select source format (OAI DC XML / DataCite XML)
2. Paste source metadata
3. Select target format (OAI DC XML / DataCite XML)
4. Click "Convert record"
```

**Output**:
```
Route summary (direct / reverse / transitive SSSOM steps)
Metrics: Applied rules, Unmapped fields, Semantic loss rules
Converted payload (XML, pretty-printed)
Download button for converted payload
[Advanced] Parsed IR (source & converted) and route details
```

**Key Functions**:
- `_parse_payload(payload, format)` → parse any source format → IR
- `resolve_conversion_route(store, source_format, target_format, sssom_dir)` → SSSOM-backed route
- `apply_mapping_rules(source_ir, rules)` → (target_ir, report)
- `_serialize_target(target_ir, format)` → IR → target format

### Benchmarking Note

Benchmarking still exists in the codebase and CLI helpers, but the Streamlit benchmark tab has been removed to keep the demo app focused on the three workflows that are presentation-critical: explore, pipeline, and convert.

For the current CLI-oriented workflow, see `BENCHMARKING.md`.

---

## 10. Orchestration & Config

### Settings

**File**: `src/kaigraph/config/settings.py`

```python
@dataclass(frozen=True)
class Settings:
    db_url: str              # default: ws://localhost:8000/rpc
    db_namespace: str        # default: kaigraph
    db_name: str             # default: crosswalk
    db_user: str             # default: root
    db_password: str         # default: root
    llm_model: str           # default: alias-fast
    embeddings_model: str    # default: sentence-transformers/all-MiniLM-L6-v2
    retrieval_top_k: int     # default: 8
```

**Environment Variables**:
- `KAIGRAPH_DB_URL`, `KAIGRAPH_DB_NS`, `KAIGRAPH_DB_NAME`, `KAIGRAPH_DB_USER`, `KAIGRAPH_DB_PASSWORD`
- `KAIGRAPH_LLM_MODEL`, `KAIGRAPH_EMBEDDINGS_MODEL`, `KAIGRAPH_RETRIEVAL_TOP_K`
- `KAIGRAPH_USE_SURREAL` (0 or 1)
- `BLABLADOR_API_KEY`, `BLABLADOR_BASE_URL`

### Pipeline Orchestration

**File**: `src/kaigraph/rdamsc/pipeline.py`

```python
run_bootstrap_pipeline(
    store: CrosswalkStore,
    output_dir: Path,
    force: bool = False,
    only_crosswalk_id: str? = None,
    logger: Callable[[str], None]? = None
) → Dict[str, object]
```

**Steps**:
1. `sync_rdamsc_catalog()` → fetch all mappings from API
2. For each crosswalk (or filtered by `only_crosswalk_id`):
   - Check status: skip if ready and not force
   - Call `ingest_rdamsc_crosswalk_docs()` → extract rules
   - Get `CrosswalkBundle` → validate rules
   - Write SSSOM TSV → `{output_dir}/{crosswalk_id}.sssom.tsv`
   - Log progress via `logger(message)`
3. Save pipeline status JSON → `.local/rdamsc_pipeline_status.json`

**Status Tracking**:
```python
status_map: Dict[crosswalk_id, {
    "crosswalk_id": str,
    "msc_id": str,
    "name": str,
    "status": str,
    "label": str,
    "result": Dict,
    "updated_at": ISO timestamp
}]
```

---

## 11. End-to-End Execution Flow

### Scenario 1: Full Bootstrap Pipeline

**User Command**:
```bash
uv run python -m kaigraph.cli.main bootstrap-rdamsc --sssom-dir exports/sssom --verbose
```

**Execution Flow**:
```
run_cli(["bootstrap-rdamsc", ...])
  └─ build_default_store()
      ├─ Check KAIGRAPH_USE_SURREAL env var
      └─ Return InMemoryCrosswalkStore or SurrealCrosswalkStore
  
  └─ run_bootstrap_pipeline(store, Path("exports/sssom"), force=False)
      
      ├─ sync_rdamsc_catalog(store)
      │   ├─ RDAMSCClient.list_mappings() → ~40 items
      │   └─ For each: extract source/target standards, create CrosswalkRecord
      │
      └─ For each CrosswalkRecord (e.g., rdamsc_c5):
          
          ├─ ingest_rdamsc_crosswalk_docs(store, crosswalk_id, sssom_dir)
          │   ├─ Fetch mapping detail from RDAMSC API
          │   ├─ For each artifact location:
          │   │   └─ fetch_artifact_text(url)
          │   │       └─ [MarkItDown | pypdf | HTMLParser | LibreOffice]
          │   │
          │   ├─ _persist_artifacts_in_kg(store, crosswalk, artifacts)
          │   │   └─ Create ArtifactDocumentRecord + ArtifactChunkRecords
          │   │
          │   ├─ Merge artifact markdown
          │   ├─ Select strategy (deterministic_pdf | deterministic_html | generic | llm)
          │   │
          │   ├─ If generic/llm:
          │   │   ├─ extract_deterministic_candidates(markdown)
          │   │   │   ├─ normalize_text_for_deterministic()
          │   │   │   ├─ extract_assignment_candidates() → ~50 rules
          │   │   │   ├─ extract_markdown_table_candidates() → ~10 rules
          │   │   │   └─ Deduplicate → 60 rules
          │   │   │
          │   │   └─ If ≥ 8 rules:
          │   │       ├─ _ingest_candidate_records() → persist rules
          │   │       └─ [Optional] _ingest_with_llm() → +20 rules via Blablador
          │   │
          │   ├─ store.get_crosswalk_bundle(crosswalk_id)
          │   │   └─ Assemble: crosswalk + standards + all rules + evidence
          │   │
          │   └─ write_bundle_sssom(bundle, exports/sssom/rdamsc_c5.sssom.tsv)
          │       └─ bundle_to_sssom_tsv()
          │           └─ YAML header + TSV rows (record_id, subject, predicate, object, ...)
          │
          └─ Emit: "[rdamsc_c5] Wrote SSSOM: exports/sssom/rdamsc_c5.sssom.tsv (80 rules)"
      
      └─ Save status JSON: .local/rdamsc_pipeline_status.json
```

**Output**:
```json
{
  "total_synced": 40,
  "total_ingested": 38,
  "total_rules": 2840,
  "crosswalks": [
    {
      "msc_id": "msc:c5",
      "crosswalk_id": "rdamsc_c5",
      "status": "ready",
      "rules": 80,
      "strategy": "deterministic_generic_augmented"
    },
    ...
  ]
}
```

### Scenario 2: Single Record Conversion in Streamlit

**User Interaction (Tab 4: Convert)**:

```
1. Select crosswalk (RDA → Dublin Core)
2. Paste OAI DC XML:
   <oai_dc:dc>
     <dc:title>Example</dc:title>
     <dc:creator>Smith, Alice</dc:creator>
   </oai_dc:dc>
3. Click "Convert and compare"
```

**Execution**:
```
_parse_payload(xml_text, "oai_dc_xml")
  └─ parse_oai_dc_xml_to_ir(xml_text)
      └─ ElementTree.parse() → extract dc:* and dcterms:* elements
      └─ Return: {
           "dcterms:title": [IRValue(text="Example")],
           "dcterms:creator": [IRValue(text="Smith, Alice")]
         }

apply_mapping_rules(source_ir, rules)
  ├─ rules loaded from CrosswalkBundle
  ├─ For rule: source_paths=["title"] → target_paths=["dcterms:title"]
  │   └─ Copy IRValue from source → target
  ├─ Track applied_rule_ids = ["rule_123", ...]
  └─ Return: (target_ir, ApplyReport)

_serialize_target(target_ir, "oai_dc_xml")
  └─ ir_to_dublin_core_xml(target_ir)
      └─ Build <rdf:RDF> with dc: + dcterms: elements
      └─ Return: XML string

_render_report(converted_ir, report, expected_ir?)
  ├─ Display metrics: 2 rules applied, 0 unmapped, 0 semantic loss
  ├─ [Optional] Compare with expected → 100% field coverage, 100% value overlap
  └─ Show transformed XML + download button
```

### Scenario 3: Deterministic PDF Parsing

**File**: `src/kaigraph/ingest/pdf_crosswalk_parser.py`

For DataCite↔Dublin Core PDF:

```
parse_mapping_pdf(pdf_path)
  └─ PdfReader(pdf_path).pages
      └─ Extract text from each page
  
  └─ parse_mapping_page_texts(page_texts)
      ├─ For each line matching ID_RE (e.g., "1.2 Identifier ...")
      │   ├─ Extract DataCite property name
      │   ├─ Find target: split on "dcterms:" or "Not present in Dublin Core"
      │   └─ Create ParsedMappingRow
      │
      ├─ For subsequent lines (cases, notes):
      │   ├─ If contains "dcterms:" → conditional mapping
      │   └─ If contains "concatenate" → aggregation
      │
      └─ Return: [ParsedMappingRow]
          ├─ row_id: "1.2"
          ├─ datacite_property: "Identifier"
          ├─ dublin_core: "dcterms:identifier"
          ├─ mapping_type: DIRECT
          ├─ confidence: 0.95
          └─ cases: [(condition, value), ...]
```

Then in `ingest_datacite_to_dc_pdf()`:
- Create StandardRecord for DataCite & Dublin Core
- For each row: create ElementRecord + MappingRuleRecord + EvidenceRecord

---

## Summary

### Current Pipeline Snapshot

Using the frozen analytics in `exports/pipeline/latest/rdamsc_stats_summary.json` and provenance in `exports/sssom/generation_manifest.json`:

- total crosswalks: `37`
- ready: `19` (`51.35%`)
- failed_unreachable: `11` (`29.73%`)
- failed_parse: `7` (`18.92%`)
- artifact fetch success rate: `71.11%`
- deterministic generic was enough for `rdamsc_c36` and `rdamsc_c38`
- `rdamsc_c38` is now ready with `160` rules and an authoritative SSSOM export

**Kaigraph Data Flow**:

```
RDAMSC API
    ↓ (sync)
[Standard, Crosswalk, Element]
    ↓ (fetch artifacts)
[ArtifactDocument, ArtifactChunk]
    ↓ (extract rules: deterministic | LLM | hybrid)
[MappingRule, Evidence]
    ↓ (persist)
SurrealDB | In-Memory Store
    ↓ (export)
SSSOM TSV (authoritative)
    ↓ (load & apply)
IR Conversion: Source Format → Target Format
    ↓ (compare)
Benchmark Metrics: Coverage, Overlap, Semantic Loss
```

**Key Components**:

1. **Sync & Ingest**: RDAMSC API → artifact fetching → markdown normalization
2. **Extraction**: Deterministic (regex, table parsing) + LLM (Blablador)
3. **Storage**: Pydantic models + SurrealDB graph
4. **Transform**: Parsers (XML/JSON → IR) + Rule application + Serializers (IR → XML)
5. **Validation**: Benchmark metrics (field coverage, value overlap, semantic loss)
6. **Export**: SSSOM TSV (authoritative) + JSON/CSV reports
7. **UI**: Streamlit tabs for browsing, pipeline runs, and single-record conversion, with benchmark work kept in CLI/report flows

---

**Last Updated**: March 10, 2026
