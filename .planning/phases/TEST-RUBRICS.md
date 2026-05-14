# Detailed Test Rubrics

**Project:** m2s3om_graph  
**Reference:** Evaluation Strategy document (`EVAL-STRATEGY.md`)  
**Status:** Draft - 2026-05-08

---

## 1. Ingestion Pipeline Rubrics

### 1.1 PDF Rule Extraction

**Test Target:** `tests/test_pdf_crosswalk_parser.py`

#### Rubric 1.1.1: Rule Extraction Completeness
```python
# Expected: Extract ≥90% of mapping rules from authoritative PDF
def test_real_pdf_is_parsable_if_available(datacite_mapping_pdf_path: Path) -> None:
    from m2s3om_graph.ingest.pdf_crosswalk_parser import parse_mapping_pdf
    
    rows = parse_mapping_pdf(datacite_mapping_pdf_path)
    # Authoritative PDF contains 35 mapping rules
    assert len(rows) >= 31, "Should extract ≥90% of 35 rules"
```

**PASS:** ≥31 rules extracted  
**FAIL:** <31 rules or exception

---

#### Rubric 1.1.2: Mapping Type Classification

```python
def test_parser_extracts_expected_rows() -> None:
    page_text = """5 publicationYear dcterms:issued
                   1.a identifierType Not present in Dublin Core
                   12.b relationTypeii
                   isPartOf dcterms:isPartOf"""
    
    rows = parse_mapping_page_texts([page_text], doc_uri="file:///tmp/mapping.pdf")
    
    # Check DIRECT mapping (rule 5)
    assert rows[0].mapping_type == MappingType.DIRECT
    
    # Check MISSING mapping (rule 1.a)
    assert rows[1].mapping_type == MappingType.MISSING
    
    # Check CONDITIONAL mapping (rule 12.b)
    assert rows[2].mapping_type == MappingType.CONDITIONAL
    assert any(case.key == "isPartOf" for case in rows[2].cases)
```

**PASS:** All mapping types classified correctly  
**FAIL:** Incorrect classification

---

#### Rubric 1.1.3: Case Extraction for Conditional Rules

```python
def test_parser_extract_conditional_cases() -> None:
    page_text = """12.b relationType
    isPartOf dcterms:isPartOf
    created dcterms:created"""
    
    rows = parse_mapping_page_texts([page_text])
    conditional_rule = next(r for r in rows if r.row_id == "12.b")
    
    # Must extract both cases exactly
    cases_dict = {c.key: c.value for c in conditional_rule.cases}
    assert "isPartOf" in cases_dict
    assert cases_dict["isPartOf"] == "dcterms:isPartOf"
    assert "created" in cases_dict
    assert cases_dict["created"] == "dcterms:created"
```

**PASS:** All cases extracted with exact key/value  
**FAIL:** Missing cases or incorrect values

---

### 1.2 Crosswalk Ingestion

**Test Target:** `tests/test_integration_e2e.py`

#### Rubric 1.2.1: End-to-End Ingestion

```python
def test_end_to_end_ingest_and_transform(datacite_mapping_pdf_path: Path) -> None:
    store = InMemoryCrosswalkStore()
    crosswalk_id = ingest_datacite_to_dc_pdf(store, datacite_mapping_pdf_path)
    bundle = store.get_crosswalk_bundle(crosswalk_id)
    
    # Must have rules and source/target standards
    assert bundle is not None
    assert len(bundle.rules) > 20
    assert bundle.source_standard is not None
    assert bundle.target_standard is not None
```

**PASS:** Bundle retrieved with rules and standards  
**FAIL:** Missing bundle, no rules, or missing standards

---

## 2. Transformation Engine Rubrics

### 2.1 Direct Mapping

**Test Target:** `tests/test_transform_apply.py`

#### Rubric 2.1.1: Direct Copy Rule

```python
def test_apply_direct_copy() -> None:
    source_ir = {}
    add_ir_value(source_ir, "publicationYear", IRValue(text="2025"))
    
    rules = [MappingRuleRecord(
        id="r1",
        source_paths=["publicationYear"],
        target_paths=["dcterms:issued"],
        mapping_type=MappingType.DIRECT,
        transform={"op": "copy"},
    )]
    
    target_ir, report = apply_mapping_rules(source_ir, rules)
    
    assert target_ir["dcterms:issued"][0].text == "2025"
    assert report.applied_rule_ids == ["r1"]
    assert len(report.semantic_loss_rules) == 0
```

**PASS:** Value copied exactly, no semantic loss  
**FAIL:** Value changed, dropped, or loss tracked

---

### 2.2 Conditional Mapping

#### Rubric 2.2.1: Value Map Transformation

```python
def test_apply_conditional_value_map() -> None:
    source_ir = {}
    add_ir_value(source_ir, "relationType", IRValue(text="isPartOf"))
    add_ir_value(source_ir, "relatedIdentifier", IRValue(text="doi:10.1/xyz"))
    
    rules = [MappingRuleRecord(
        id="r3",
        source_paths=["relatedIdentifier"],
        target_paths=["dcterms:relation"],
        mapping_type=MappingType.CONDITIONAL,
        transform={
            "op": "value_map",
            "field": "relationType",
            "mapping": {"isPartOf": "dcterms:isPartOf"},
            "default": "dcterms:relation",
        },
    )]
    
    target_ir, report = apply_mapping_rules(source_ir, rules)
    
    # Should map to dcterms:isPartOf based on relationType value
    assert "dcterms:isPartOf" in target_ir
    assert target_ir["dcterms:isPartOf"][0].text == "doi:10.1/xyz"
```

**PASS:** Conditional mapping applied correctly  
**FAIL:** Default used or mapping ignored

---

### 2.3 Semantic Loss Tracking

#### Rubric 2.3.1: Missing Field Handling

```python
def test_apply_missing_fields_track_loss() -> None:
    source_ir = {}
    add_ir_value(source_ir, "identifierType", IRValue(text="DOI"))
    
    rules = [MappingRuleRecord(
        id="r2",
        source_paths=["identifierType"],
        target_paths=[],
        mapping_type=MappingType.MISSING,
        semantic_loss=True,
    )]
    
    target_ir, report = apply_mapping_rules(source_ir, rules)
    
    # Rule applied but produces no output
    assert "identifierType" not in target_ir or target_ir["identifierType"] == []
    assert report.applied_rule_ids == ["r2"]
    assert "r2" in report.semantic_loss_rules
```

**PASS:** Loss tracked in report  
**FAIL:** Loss not recorded

---

### 2.4 IR Value Integrity

#### Rubric 2.4.1: Source Provenance Preservation

```python
def test_ir_value_source_tracking() -> None:
    source_ir = {}
    value = IRValue(
        text="2025",
        source_record_id="rec123",
        source_path="publicationYear",
        source_format="oai_dc",
    )
    add_ir_value(source_ir, "publicationYear", value)
    
    # Transform...
    target_ir, _ = apply_mapping_rules(source_ir, rules)
    
    # Provenance should persist
    assert target_ir["dcterms:issued"][0].source_record_id == "rec123"
    assert target_ir["dcterms:issued"][0].source_path == "publicationYear"
```

**PASS:** Provenance preserved through transformation  
**FAIL:** Provenance lost

---

## 3. CLI Operations Rubrics

### 3.1 demo-convert Command

**Test Target:** `tests/test_cli_fast.py`

#### Rubric 3.1.1: Command Execution

```python
def test_cli_demo_convert_fast() -> None:
    # Should complete without error and produce output
    code = run_cli(["demo-convert"])
    
    assert code == 0, "Should exit with success"
```

**PASS:** Exit code 0  
**FAIL:** Non-zero exit or exception

---

### 3.2 Error Handling

#### Rubric 3.2.1: Missing PDF Path Validation

```python
def test_cli_ingest_pdf_path_validation() -> None:
    missing = Path("/tmp/does_not_exist_crosswalk.pdf")
    code = run_cli(["ingest-pdf", "--pdf", str(missing)])
    
    # User error should return code 2
    assert code == 2, "Should return user error code"
```

**PASS:** Exit code 2 (user error)  
**FAIL:** Crash (code 1) or wrong exit code

---

### 3.3 Benchmark Fixture

#### Rubric 3.3.1: Benchmark Generation

```python
def test_cli_benchmark_fixture_fast() -> None:
    code = run_cli(["benchmark-fixture"])
    
    assert code == 0, "Should generate benchmark dataset"
    # Optional: Assert benchmark file exists
```

**PASS:** Exit code 0 and dataset created  
**FAIL:** Exit non-zero or no dataset

---

## 4. Streamlit UI Rubrics

### 4.1 Tab Rendering

**Test Target:** `tests/test_app_entry_and_system.py`

#### Rubric 4.1.1: Main Entry Renders Tabs

```python
def test_app_main_renders_expected_tabs(monkeypatch) -> None:
    # Mock streamlit calls
    tab_labels: list[str] = []
    
    monkeypatch.setattr(app_entry.st, "tabs", lambda labels: tab_labels.extend(labels))
    
    app_entry.main()
    
    expected = [
        "1) Crosswalk Browser",
        "2) Pipeline", 
        "3) Convert One Record",
    ]
    
    assert tab_labels == expected
```

**PASS:** All three expected tabs rendered  
**FAIL:** Missing/incorrect tabs

---

### 4.2 Environment Display

#### Rubric 4.2.1: API Key Status

```python
def test_system_env_rows_reflects_key_presence(monkeypatch) -> None:
    # Missing key
    monkeypatch.delenv("BLABLADOR_API_KEY", raising=False)
    rows = system._env_rows()
    assert rows["BLABLADOR_API_KEY"] == "missing"
    
    # Present key
    monkeypatch.setenv("BLABLADOR_API_KEY", "token")
    rows = system._env_rows()
    assert rows["BLABLADOR_API_KEY"] == "loaded"
```

**PASS:** Status reflects actual environment  
**FAIL:** Incorrect status

---

### 4.3 Model Fetching

#### Rubric 4.3.1: Model Cache Error Handling

```python
def test_fetch_blablador_models_cached_missing_key() -> None:
    models, error = system._fetch_blablador_models_cached("https://example.org/v1", " ")
    
    assert models == []
    assert error == "BLABLADOR_API_KEY is missing"
```

**PASS:** Graceful error handling with clear message  
**FAIL:** Exception or unclear message

---

## 5. Store & Repository Rubrics

### 5.1 Bundle Persistence

**Test Target:** `tests/test_app_state.py`

#### Rubric 5.1.1: Bundle Round-trip

```python
def test_seed_store_from_sssom_exports(tmp_path: Path) -> None:
    bundle = CrosswalkBundle(...)
    write_bundle_sssom(bundle, tmp_path / "rdamsc_c999.sssom.tsv")
    
    store = InMemoryCrosswalkStore()
    seeded_rules = _seed_store_from_sssom_exports(store, tmp_path)
    
    assert seeded_rules == 1
    bundle_loaded = store.get_crosswalk_bundle("rdamsc_c999")
    assert bundle_loaded is not None
    assert len(bundle_loaded.rules) == len(bundle.rules)
```

**PASS:** Bundle intact after SSSOM round-trip  
**FAIL:** Data loss or mismatch

---

### 5.2 Standards Management

#### Rubric 5.2.1: Standards Creation

```python
def test_standards_created_on_bundle_ingest() -> None:
    store = InMemoryCrosswalkStore()
    # Ingest bundle with source/target standards
    crosswalk_id = ingest_datacite_to_dc_pdf(store, pdf_path)
    
    standards = store.list_standards()
    standard_names = {s.name for s in standards}
    
    assert "DataCite" in standard_names
    assert "Dublin Core" in standard_names
```

**PASS:** Both source and target standards created  
**FAIL:** Missing standards

---

## 6. Quality Thresholds

| Dimension | Pass Threshold | Sample Size |
|-----------|----------------|-------------|
| PDF Rule Extraction Completeness | ≥90% | 35 rules (DataCite→DC) |
| Mapping Type Classification | 100% | All rule types |
| Direct Mapping Accuracy | 100% | ≥10 test cases |
| Conditional Mapping Accuracy | 100% | ≥5 test cases |
| CLI Command Success | 100% | All commands |
| UI Tab Rendering | 100% | All tabs |

---

## 7. Measurement Tools

| Dimension | Measurement Method |
|-----------|-------------------|
| Rule Extraction | Code: Compare parsed vs expected count |
| Mapping Type | Code: Assert `rule.mapping_type == expected` |
| Transformation | Code: Assert `target_ir[key][0].text == expected` |
| Semantic Loss | Code: Assert `"rule_id" in report.semantic_loss_rules` |
| CLI Exit Code | Code: Assert `code == expected` |
| UI Rendering | Code (mocked): Assert tab labels match |
| Bundle Persistence | Code: Compare before/after count |

---

**Status:** Draft  
**Next Step:** Review with domain experts  
**Last Updated:** 2026-05-08
