# Testing & Evaluation Guide

**Project:** m2s3om_graph - Metadata Standards Mapping Tool  
**Last Updated:** 2026-05-08

---

## Quick Start

### Run All Tests
```bash
uv run --with pytest pytest
```

### Run Tests by Category
```bash
# Ingestion tests
uv run --with pytest pytest tests -k "pdf or ingest"

# Transformation tests
uv run --with pytest pytest tests -k "transform"

# CLI tests
uv run --with pytest pytest tests -k "cli"

# UI tests
uv run --with pytest pytest tests -k "app"
```

### Run Demo and Verify Output
```bash
uv run python -m m2s3om_graph.cli.main demo-convert
```

Expected output:
```json
{"applied_rules": 31, "unmapped": 140, "xml_preview": "<oai_dc:dc..."}
```

---

## Test Coverage

### Core Modules (100% Pass Rate)

| Module | Tests | Status |
|--------|-------|--------|
| PDF Parser | `test_pdf_crosswalk_parser.py` | ✓ |
| Transform Engine | `test_transform_apply.py` | ✓ |
| CLI Operations | `test_cli_fast.py` | ✓ |
| Streamlit UI | `test_app_entry_and_system.py` | ✓ |
| Store & Repository | `test_app_state.py`, `test_sssom.py` | ✓ |

### Full Test Suite Summary (113 tests)
- **113 passed** in ~4 seconds
- No failing tests
- No deprecation warnings

---

## Evaluation Strategy Documents

### `/planning/phases/EVAL-STRATEGY.md`
Comprehensive evaluation strategy including:
- System overview and type classification
- 5 evaluation dimensions with rubrics
- Reference datasets
- Tooling recommendations
- CI/CD integration examples
- Quality gates
- Success metrics

### `/planning/phases/TEST-RUBRICS.md`
Detailed rubrics for each test case:
- Pass/fail criteria
- Expected behavior examples
- Code snippets for each rubric

---

## Quality Gates

### Local Development
```bash
# All tests must pass
uv run --with pytest pytest

# Or run specific category
uv run --with pytest pytest tests -k "transform"
```

### Pre-commit Hook
Add to `.pre-commit-config.yaml`:
```yaml
- repo: local
  hooks:
    - id: pytest-check
      name: pytest
      entry: uv run --with pytest pytest tests
      language: system
      types: [python]
      pass_filenames: false
```

### CI Pipeline
```yaml
- name: Run tests
  run: uv run --with pytest pytest tests -v --tb=short

- name: Upload coverage reports
  uses: codecov/codecov-action@v4
  with:
    files: ./coverage.xml
```

---

## Key Dimensions & Rubrics

### 1. PDF Rule Extraction (Critical)
**PASS:** Extracts ≥90% of rules from DataCite→DC PDF  
**FAIL:** Missing rules or incorrect parsing

### 2. Mapping Type Classification (Critical)
**PASS:** DIRECT, CONDITIONAL, MISSING, AGGREGATION, PASSTHROUGH correctly classified  
**FAIL:** Wrong mapping type

### 3. Direct Mapping (Critical)
**PASS:** Source field copied to target with exact value  
**FAIL:** Value modified or dropped

### 4. Conditional Mapping (Critical)
**PASS:** Value mapping applied correctly based on condition  
**FAIL:** Default used or condition ignored

### 5. Semantic Loss Tracking (Critical)
**PASS:** Lossy rules tracked in report  
**FAIL:** Loss not recorded

### 6. CLI demo-convert (Critical)
**PASS:** Exit code 0 with output  
**FAIL:** Non-zero exit

### 7. UI Tab Rendering (High)
**PASS:** Three expected tabs render correctly  
**FAIL:** Missing/incorrect tabs

---

## Next Steps for Test Expansion

### 1. Expand PDF Parser Tests
- Add ground truth fixture for DataCite→DC PDF (35 rules expected)
- Test edge cases: malformed PDFs, encoding issues

### 2. Add Transformation Edge Cases
- Empty IR input
- Multi-value fields
- Path mismatches

### 3. Create Mock Database Fixture
- SurrealDB integration tests
- Full DB round-trip verification

### 4. Document demo-convert Output
- Assert output JSON structure
- Check applied_rules count

### 5. Add Streamlit Smoke Test
- Import `app/app.py`
- Verify main() doesn't crash

---

## Current Test Statistics

| Category | Count | Status |
|----------|-------|--------|
| **Total Tests** | 113 | ✓ All passing |
| **Ingestion** | ~15 | ✓ |
| **Transformation** | ~10 | ✓ |
| **CLI** | 3 | ✓ |
| **UI/Streamlit** | 4 | ✓ |
| **Store/Repository** | 4 | ✓ |
| **RAG/LLM** | ~20 | ✓ |
| **Integration** | ~3 | ✓ |
| **Other Utilities** | ~54 | ✓ |

---

## References

- **Evaluation Strategy:** `.planning/phases/EVAL-STRATEGY.md`
- **Detailed Rubrics:** `.planning/phases/TEST-RUBRICS.md`
- **Architecture:** `.planning/codebase/ARCHITECTURE.md`
- **Testing Patterns:** `.planning/codebase/TESTING.md`

---

**Maintainer:** Development Team  
**Review Cycle:** Quarterly or phase transitions
