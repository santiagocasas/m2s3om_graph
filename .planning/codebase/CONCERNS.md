# Codebase Concerns

**Analysis Date:** 2026-05-08

## Tech Debt

**RDAMSC Ingestion Module:**
- Issue: `src/m2s3om_graph/rdamsc/ingest.py` has become a "god file" (1018 lines), mixing high-level orchestration, specific deterministic parsing logic for various sources, and LLM extraction workflows.
- Files: `src/m2s3om_graph/rdamsc/ingest.py`
- Impact: High cognitive load for maintainers; difficult to test individual parsing strategies in isolation.
- Fix approach: Split the file into a service orchestrator (`ingest_service.py`), a dedicated module for deterministic parsers (`deterministic_parsers.py`), and a separate LLM extraction handler (`llm_extractor.py`).

**UI and Business Logic Coupling:**
- Issue: Streamlit view files contain significant business logic for filtering, statistics calculation, and status resolution.
- Files: `app/views/crosswalks.py`, `app/views/transform.py`
- Impact: Business logic is not reusable outside the UI and is harder to unit test without mocking the Streamlit environment.
- Fix approach: Extract logic (e.g., `_filter_rules`, `_status_counts`) into a separate service layer within `src/m2s3om_graph/`.

## Known Bugs

Not detected during initial scan.

## Security Considerations

**Raw Query Execution:**
- Risk: `SurrealCrosswalkStore` relies on raw SurrealQL strings. While parameters are currently used correctly, this pattern is more prone to errors and harder to validate than using a structured query builder.
- Files: `src/m2s3om_graph/db/crosswalk_repository.py`
- Current mitigation: Use of parameterized queries (`$id`, `$obj`).
- Recommendations: Evaluate if a more formal ORM or query builder pattern is needed as the schema grows.

## Performance Bottlenecks

**N+1 Query Pattern in Bundle Retrieval:**
- Problem: `get_crosswalk_bundle` in `SurrealCrosswalkStore` fetches evidence by performing a separate query for every mapping rule in the bundle.
- Files: `src/m2s3om_graph/db/crosswalk_repository.py`
- Cause: Sequential queries within a loop.
- Improvement path: Replace the loop with a single query using an `IN` clause or a SurrealQL `FETCH` / `JOIN` to retrieve all evidence for the bundle's rules in one round trip.

## Fragile Areas

**Defensive Return Patterns:**
- Files: `src/m2s3om_graph/crosswalk/route.py`, `src/m2s3om_graph/db/crosswalk_repository.py`, `src/m2s3om_graph/sssom.py`
- Why fragile: Heavy reliance on `return []` or `return None` when types don't match or data is missing. While defensive, it can mask underlying data integrity issues or unexpected API responses from the DB.
- Safe modification: Implement more explicit error handling or use a Result-type pattern to distinguish between "empty result" and "unexpected error/type".
- Test coverage: Basic tests exist, but edge cases for these "empty" returns may be under-tested.

## Scaling Limits

Not detected.

## Dependencies at Risk

Not detected.

## Missing Critical Features

Not detected.

## Test Coverage Gaps

**Edge Case Ingestion:**
- What's not tested: Robustness of deterministic parsers against malformed or unexpected HTML/PDF structures from RDAMSC.
- Files: `src/m2s3om_graph/rdamsc/ingest.py`
- Risk: Ingestion pipeline may crash or produce silent data loss when encountering non-standard document layouts.
- Priority: Medium

---

*Concerns audit: 2026-05-08*
