# Testing Patterns

**Analysis Date:** 2026-05-08

## Test Framework

**Runner:**
- `pytest` (Version 8.3.0+)
- Config: `pyproject.toml` (`[tool.pytest.ini_options]`)

**Assertion Library:**
- Standard `assert` statements.

**Run Commands:**
```bash
uv run --with pytest pytest              # Run all tests
uv run --with pytest pytest tests/test_file.py # Run one file
uv run --with pytest pytest tests -k filter    # Run filtered tests
```

## Test File Organization

**Location:**
- Separate `tests/` directory at the root.

**Naming:**
- Test files are prefixed with `test_` (e.g., `tests/test_errors.py`).

**Structure:**
```
tests/
├── fixtures/             # Static data files (XML, PDF)
├── conftest.py           # Shared fixtures
└── test_*.py             # Test suites
```

## Test Structure

**Suite Organization:**
```typescript
def test_function_name(fixture_name) -> None:
    # Arrange
    input_data = ...
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result == expected_output
```

**Patterns:**
- **Setup:** Use of `@pytest.fixture` in `conftest.py` or local to the test file for shared resources.
- **Teardown:** Handled by pytest fixtures or `tmp_path` for filesystem cleanup.
- **Assertion:** Direct equality checks and membership tests.

## Mocking

**Framework:** `pytest` built-in `monkeypatch` fixture.

**Patterns:**
```typescript
def test_with_mock(monkeypatch) -> None:
    # Patching an attribute/function
    monkeypatch.setattr("m2s3om_graph.oai.client.requests.get", _fake_get)
    
    # Patching environment variables
    monkeypatch.setenv("BLABLADOR_API_KEY", "test-key")
    monkeypatch.delenv("SOME_VAR", raising=False)
```

**What to Mock:**
- External API calls (e.g., `requests.get`).
- Environment variables.
- Heavy dependencies or system state that would make tests slow or flaky.

**What NOT to Mock:**
- Internal Pydantic models and data structures.
- Core transformation logic.

## Fixtures and Factories

**Test Data:**
- Static files are stored in `tests/fixtures/` (e.g., `tests/fixtures/oai_list_formats.xml`).
- Pydantic models are used to create structured test data on the fly (e.g., `MappingRuleRecord` in `tests/test_transform_apply.py`).

**Location:**
- Shared Python fixtures in `tests/conftest.py`.

## Coverage

**Requirements:** Not explicitly enforced in `pyproject.toml`.

**View Coverage:**
- Typically run via `pytest-cov` (not explicitly configured in `pyproject.toml` but supported by `pytest`).

## Test Types

**Unit Tests:**
- High volume of tests focusing on individual functions and models (e.g., `tests/test_errors.py`).

**Integration Tests:**
- End-to-end flows are tested in `tests/test_integration_e2e.py`.

**E2E Tests:**
- Covered by the integration tests and the `demo-convert` CLI smoke test.

## Common Patterns

**Async Testing:**
- Not detected (the codebase appears to be primarily synchronous).

**Error Testing:**
```typescript
def test_error_condition():
    with pytest.raises(ValueError):
        function_that_fails()
```
(Note: While `pytest.raises` is standard, current tests often check structured error payloads via `make_error_payload`).

---

*Testing analysis: 2026-05-08*
