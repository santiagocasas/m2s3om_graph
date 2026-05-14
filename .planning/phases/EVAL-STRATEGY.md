# Evaluation Strategy

**Created:** 2026-05-08  
**Project:** m2s3om_graph - Metadata Standards Mapping Tool  
**Reference:** `ai-evals.md` evaluation framework

---

## 1. System Overview

**Type:** Hybrid (RAG + Content Generation + Transform Pipeline)  
**Framework:** Domain-specific metadata crosswalk engine with SurrealDB persistence  
**Phase:** Core functionality validation (ingestion, transformation, UI)

### Core Capabilities
- PDF mapping document ingestion with rule extraction
- Metadata record transformation via intermediate representation
- Graph-based transitive mapping between standards
- Semantic loss tracking and evidence preservation
- Streamlit-based interactive visualization UI

---

## 2. Evaluation Dimensions

### 2.1 Ingestion Pipeline (Critical)

**Dimension:** PDF crosswalk extraction fidelity  
**Primary concern:** Rule extraction accuracy from PDF documents

| Dimension | Rubric | Measurement | Priority |
|-----------|--------|-------------|----------|
| **Rule Extraction Completeness** | PASS: Extracts ≥90% of mapping rules from authoritative PDF (e.g., DataCite→DC) with correct structure<br>FAIL: Missing rules, incorrect field parsing, or malformed mapping types | Code: Compare parsed rows against known ground truth (fixture or manual count) | Critical |
| **Mapping Type Classification** | PASS: Correctly classifies DIRECT, CONDITIONAL, MISSING, AGGREGATION, PASSTHROUGH<br>FAIL: Misclassified mapping type changes transformation behavior | Code: Assert `rule.mapping_type == expected_type` per test fixture | Critical |
| **Case Handling for Conditional Rules** | PASS: Extracts all conditional mappings (e.g., `relationType → dcterms:isPartOf`) with exact key/value pairs<br>FAIL: Missing or incorrect case mappings | Code: Assert `case.key` and `case.value` match expected values | High |
| **Evidence Preservation** | PASS: Every parsed rule contains source reference (doc_uri, page_number, snippet)<br>FAIL: Rules without traceability metadata | Code: Assert `rule.snippet` and `rule.page_number` present | High |

**Test Coverage:**
- Unit: `test_pdf_crosswalk_parser.py` (existing - expand)
- Integration: `test_integration_e2e.py` (existing - expand)

---

### 2.2 Transformation Engine (Critical)

**Dimension:** Rule application correctness and IR handling  
**Primary concern:** Accurate record transformation with semantic loss tracking

| Dimension | Rubric | Measurement | Priority |
|-----------|--------|-------------|----------|
| ** DIRECT Mapping** | PASS: Source field copied to target with exact value, no loss<br>FAIL: Value modified, dropped, or wrong target path | Code: `assert target_ir["dcterms:issued"][0].text == "2025"` | Critical |
| ** CONDITIONAL Mapping** | PASS: Value mapping applied correctly (e.g., `relationType="isPartOf" → dcterms:isPartOf`) | Code: Assert transformed value matches expected conditional target | Critical |
| ** SEMANTIC LOSS Tracking** | PASS: Rules marked `semantic_loss=True` appear in report's `semantic_loss_rules` list<br>FAIL: Lossy rules not tracked in report | Code: `assert "r2" in report.semantic_loss_rules` | Critical |
| ** AMBIGUITY Detection** | PASS: Ambiguous rules identified and logged in report<br>FAIL: Ambiguity not captured or reported | Code: Assert ambiguity count in report | Medium |
| ** IR Integrity** | PASS: IRValue source tracking preserved (source_record_id, source_path, source_format)<br>FAIL: Source provenance lost during transformation | Code: Check IRValue.attrs contain expected provenance | Medium |

**Test Coverage:**
- Unit: `test_transform_apply.py` (existing - comprehensive)
-扩展: Add edge cases for concatenation, splitting, value mapping

---

### 2.3 CLI Operations (High)

**Dimension:** Command-line interface correctness and error handling  
**Primary concern:** CLI commands execute successfully with expected side effects

| Dimension | Rubric | Measurement | Priority |
|-----------|--------|-------------|----------|
| **demo-convert Command** | PASS: `run_cli(["demo-convert"])` exits with code 0, produces output<br>FAIL: Non-zero exit or no output generated | Code: Assert exit code == 0 | Critical |
| **PDF Ingestion Validation** | PASS: Invalid PDF path returns exit code 2 (user error)<br>FAIL: Crash, hang, or wrong exit code | Code: `assert code == 2` for missing file | Critical |
| **benchmark-fixture Command** | PASS: Generates benchmark dataset without errors<br>FAIL: Exception or incomplete output | Code: Assert exit code == 0 | Medium |
| **Error Message Clarity** | PASS: User-friendly errors for common misconfigurations (missing PDF, invalid DB config)<br>FAIL: Cryptic stack trace or misleading message | Human review | High |

**Test Coverage:**
- Unit: `test_cli_fast.py` (existing - expand)

---

### 2.4 Streamlit UI (Medium)

**Dimension:** Application entry point and navigation  
**Primary concern:** UI renders expected tabs and sidebar components

| Dimension | Rubric | Measurement | Priority |
|-----------|--------|-------------|----------|
| **Main Entry Renders Tabs** | PASS: Three tabs render: "1) Crosswalk Browser", "2) Pipeline", "3) Convert One Record"<br>FAIL: Missing tabs or incorrect labels | Code (mocked): Assert tab labels match expected | High |
| **Sidebar Renders** | PASS: `system.render_sidebar()` called during startup<br>FAIL: Sidebar not invoked | Code (mocked): Assert call intercepted | High |
| **Environment Display** | PASS: `_env_rows()` returns "loaded"/"missing" status correctly for required vars<br>FAIL: Incorrect status or crash on missing env | Code: Assert dict values for API key presence/absence | High |
| **Model Cache Fetch** | PASS: `_fetch_blablador_models_cached()` handles errors gracefully, returns list or error payload<br>FAIL: Unhandled exception on network failure | Code (mocked): Assert error path returns (`[]`, "error message") | Medium |

**Test Coverage:**
- Unit: `test_app_entry_and_system.py` (existing - comprehensive)
-扩展: Smoke test for app.py imports and basic structure

---

### 2.5 Store & Repository (High)

**Dimension:** Data persistence and bundle retrieval  
**Primary concern:** Crosswalk bundles load correctly from store

| Dimension | Rubric | Measurement | Priority |
|-----------|--------|-------------|----------|
| **Bundle Persistence** | PASS: Ingested crosswalk returns same rule count when retrieved<br>FAIL: Rules lost in round-trip | Code: `assert len(store.get_crosswalk_bundle(id).rules) == expected` | Critical |
| **Standards Management** | PASS: Source and target standards created/updated alongside crosswalk<br>FAIL: Standards missing or mismatched | Code: Assert `store.list_standards()` contains expected entries | High |
| **SSSOM Export Round-trip** | PASS: Bundle exported to SSSOM and re-imported maintains rule count<br>FAIL: Data loss during SSSOM conversion | Code: Compare rule count before/after export/import | High |
| **In-memory Store Isolation** | PASS: Each test gets fresh store (no state bleed)<br>FAIL: Tests interfere with each other | Code: Test passes consistently with fresh fixture | High |

**Test Coverage:**
- Unit: `test_app_state.py`, `test_sssom.py` (existing)

---

## 3. Reference Datasets

### 3.1 Fixtures (Static)

| File | Purpose | Size | Source |
|------|---------|------|--------|
| `tests/fixtures/oai_list_formats.xml` | OAI-PMH format listing for parser testing | ~2KB | Project fixture |
| `tests/fixtures/oai_getrecord_dc.xml` | OAI Dublin Core record for transformation demo | ~3KB | Project fixture |
| `/home/casas/AI/Metadata-Mappings/DataCite_DublinCore_Mapping.pdf` | Authoritative mapping PDF for ingestion validation | ~200KB | Local (user-provided) |
| `tests/fixtures/*.sssom.tsv` | SSSOM exports for round-trip testing | Variable | Generated during tests |

### 3.2 Test Datasets (Generated)

| Dataset | Size | Composition | Generation |
|---------|------|-------------|------------|
| **Ingestion Ground Truth** | 30–50 rules | Extracted from DataCite→DC PDF, manually verified | Manual |
| **Transformation Test Cases** | 20 records | Mix of DIRECT, CONDITIONAL, MISSING mappings | Pydantic factories |
| **Benchmark Fixture** | 100 records | Random Dublin Core records for CLI benchmark | `demo-convert` or synthetic |

---

## 4. Tooling Recommendations

### 4.1 Test Runner & Framework

| Concern | Tool | Configuration |
|---------|------|---------------|
| **Test Runner** | `pytest` (v8.3.0+) | `[tool.pytest.ini_options]` in `pyproject.toml` |
| **Mocking** | `monkeypatch` fixture | Built into pytest |
| **Fixture Management** | Pydantic factories + `@pytest.fixture` | `tests/conftest.py` and per-file fixtures |
| **Coverage** | `pytest-cov` (optional) | Not currently configured, can be added: `uv run --with pytest pytest --cov=src/m2s3om_graph` |

### 4.2 Observability & Tracing (Future)

| Concern | Tool | Status |
|---------|------|--------|
| **Tracing** | Arize Phoenix (open-source) | Recommended for production RAG evals |
| **Prompt Regression** | Promptfoo | Recommended for LLM-based components |
| **LangChain** | LangSmith | Only if migrating to LangChain |

---

## 5. CI/CD Integration

### 5.1 Local Test Commands

```bash
# Run all tests
uv run --with pytest pytest

# Run one test file
uv run --with pytest pytest tests/test_pdf_crosswalk_parser.py

# Run filtered tests
uv run --with pytest pytest tests -k "ingest or transform"

# Run with coverage (optional)
uv run --with pytest pytest --cov=src/m2s3om_graph --cov-report=term-missing
```

### 5.2 CI Pipeline Integration

```yaml
# .github/workflows/tests.yml
- name: Run tests
  run: uv run --with pytest pytest tests -v --tb=short

- name: Upload coverage reports
  uses: codecov/codecov-action@v4
  with:
    files: ./coverage.xml
```

### 5.3 Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: pytest-check
      name: pytest
      entry: uv run --with pytest pytest tests
      language: system
      types: [python]
      pass_filenames: false
```

---

## 6. Quality Gates

| Stage | Pass Criteria | Action on Fail |
|-------|---------------|----------------|
| **Local Dev** | `pytest tests` → 100% pass rate | Block commit, fix tests |
| **PR Check** | All new tests pass + no regressions | Block merge |
| **Release** | Critical dimensions >95% coverage | Block release |
| **Nightly** | Integration + E2E full suite | Alert on failure |

---

## 7. Current Gaps & Next Steps

### 7.1 Missing Test Coverage

| Area | Current | Target |
|------|---------|--------|
| **RAG Retrieval** | `test_retrieval_qa.py` (minimal) | Full RAG eval with faithfulness/relevance metrics |
| **LLM-based Ingestion** | `test_rdamsc_llm_extract.py` | Calibration suite for LLM extraction accuracy |
| **Semantic Loss Metrics** | Basic tracking | Quantitative loss measurement |
| **Graph Transitive Paths** | Not tested | Path discovery and cycle detection tests |
| **SurrealDB Integration** | Health check only | Full DB round-trip tests |

### 7.2 Immediate Actions

1. **Expand PDF parser tests** with ground truth fixture for DataCite→DC PDF
2. **Add transformation edge cases**: empty IR, multi-value fields, path mismatches
3. **Create mock database fixture** for SurrealDB integration tests
4. **Document expected output** for `demo-convert` (assert output structure)
5. **Add Streamlit smoke test** that imports `app/app.py` and verifies main() doesn't crash

---

## 8. Rubric Summary

### Critical Dimensions (Must Pass)
- Rule extraction completeness (PDF → rules)
- Mapping type classification accuracy
- Direct/conditional mapping transformation correctness
- CLI demo-convert command execution
- UI tab rendering (expected tabs appear)

### High Priority (Should Pass)
- Semantic loss rule tracking
- Conditional mapping case extraction
- Crosswalk bundle persistence/retrieval
- SSSOM round-trip integrity
- Environment variable status display
- Error handling for missing PDFs

### Medium Priority (Nice to Have)
- Ambiguity detection reporting
- IR provenance preservation
- Benchmark fixture generation
- LLM extraction accuracy (RDA MSC)

---

## 9. Success Metrics

| Metric | Target |
|--------|--------|
| Unit test pass rate | 100% |
| PDF ingestion rule extraction completeness | ≥90% |
| Transformation accuracy | 100% (deterministic rules) |
| CLI command success rate | 100% |
| UI tab rendering correctness | 100% |
| Critical test coverage | ≥80% of core modules |

---

**Last Updated:** 2026-05-08  
**Maintainer:** Development Team  
**Next Review:** Phase transition or quarterly
