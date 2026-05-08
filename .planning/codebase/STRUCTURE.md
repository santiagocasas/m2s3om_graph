# Codebase Structure

**Analysis Date:** 2026-05-08

## Directory Layout

```
[project-root]/
├── app/               # Streamlit web application
│   ├── views/         # UI page definitions
│   └── state.py       # Streamlit session state management
├── src/m2s3om_graph/      # Core business logic
│   ├── cli/           # CLI entry points and command handlers
│   ├── db/            # Persistence layer (Store and Models)
│   ├── ingest/        # PDF and external data ingestion
│   ├── transform/     # Transformation engine and IR
│   ├── rdamsc/        # RDAMSC domain-specific pipelines
│   ├── retrieval/     # RAG and candidate mapping logic
│   ├── qa/            # Quality assurance and evaluation
│   ├── models/        # Domain-specific data models
│   └── config/        # System configuration
├── surql/             # SurrealDB schema definitions
├── tests/             # Pytest test suite
├── exports/           # Output artifacts (SSSOM, pipeline results)
└── scripts/           # Infrastructure and helper scripts
```

## Directory Purposes

**app/:**
- Purpose: Interactive user interface.
- Contains: Streamlit app logic and view components.
- Key files: `app/app.py`, `app/views/transform.py`.

**src/m2s3om_graph/cli/:**
- Purpose: Command-line interface for administrative and batch tasks.
- Contains: Argument parsing and command dispatch logic.
- Key files: `src/m2s3om_graph/cli/main.py`.

**src/m2s3om_graph/db/:**
- Purpose: Abstract and implement data storage.
- Contains: Store interfaces, SurrealDB implementation, and DB-specific models.
- Key files: `src/m2s3om_graph/db/crosswalk_repository.py`, `src/m2s3om_graph/db/models.py`.

**src/m2s3om_graph/transform/:**
- Purpose: The "engine" that converts source records to target records.
- Contains: IR (Intermediate Representation) logic, rule application, and serializers.
- Key files: `src/m2s3om_graph/transform/apply.py`, `src/m2s3om_graph/transform/ir.py`.

**src/m2s3om_graph/ingest/:**
- Purpose: Extract metadata mappings from unstructured/semi-structured sources.
- Contains: PDF parsers and ingestion orchestrators.
- Key files: `src/m2s3om_graph/ingest/crosswalk_ingestion.py`.

**src/m2s3om_graph/rdamsc/:**
- Purpose: specialized workflows for RDAMSC standards.
- Contains: Pipeline definitions and RDAMSC-specific ingestion logic.
- Key files: `src/m2s3om_graph/rdamsc/pipeline.py`.

## Key File Locations

**Entry Points:**
- `app/app.py`: Streamlit UI entry point.
- `src/m2s3om_graph/cli/main.py`: CLI entry point.

**Configuration:**
- `src/m2s3om_graph/config/`: General system config.
- `pyproject.toml`: Build and dependency configuration.

**Core Logic:**
- `src/m2s3om_graph/transform/apply.py`: Rule application logic.
- `src/m2s3om_graph/db/crosswalk_repository.py`: Persistence orchestration.

**Testing:**
- `tests/`: All functional and integration tests.
- `tests/conftest.py`: Pytest fixtures.

## Naming Conventions

**Files:**
- Modules: `snake_case.py` (e.g., `crosswalk_repository.py`).
- View components: `snake_case.py` (e.g., `crosswalks.py`).

**Directories:**
- Package directories: `snake_case` (e.g., `m2s3om_graph/transform`).

## Where to Add New Code

**New Feature (Transformation):**
- Primary code: `src/m2s3om_graph/transform/`
- Serializers: `src/m2s3om_graph/transform/serializers.py`
- Tests: `tests/test_transform_*.py`

**New Ingestion Source:**
- Implementation: `src/m2s3om_graph/ingest/`
- Tests: `tests/test_ingest_*.py`

**New DB Entity/Field:**
- Model: `src/m2s3om_graph/db/models.py`
- Schema: `surql/schema.surql`
- Store method: `src/m2s3om_graph/db/crosswalk_repository.py`

**UI View:**
- Implementation: `app/views/`
- Integration: `app/app.py`

**Utilities:**
- Shared helpers: `src/m2s3om_graph/` (as top-level modules if general) or `scripts/helpers/` (if infra-related).

## Special Directories

**exports/:**
- Purpose: Store generated SSSOM files and pipeline results.
- Generated: Yes
- Committed: No (typically ignored)

**surql/:**
- Purpose: Source of truth for SurrealDB schema.
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-05-08*
