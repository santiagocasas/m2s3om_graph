# AGENTS.md

Guidance for coding agents working in this repository.

## Repository snapshot

- Language: Python 3.12+
- Package manager/runtime: `uv`
- Main code: `src/m2s3om_graph/`
- App entrypoint: `app/app.py`
- Surreal schema: `surql/schema.surql`

## Setup

1. Install/sync dependencies:
   - `uv sync`
2. Run tests:
   - `uv run --with pytest pytest`
3. Run Streamlit:
   - `uv run streamlit run app/app.py`
4. Run quick CLI smoke:
   - `uv run python -m m2s3om_graph.cli.main demo-convert`

## Build/lint/type-check/test commands

### Build

- Package build:
  - `uv build`

### Lint and format

- Ruff check:
  - `uv run --with ruff ruff check src app tests`
- Ruff format:
  - `uv run --with ruff ruff format src app tests`

### Type check

- BasedPyright:
  - `uv run --with basedpyright basedpyright src`

### Tests

- Run all tests:
  - `uv run --with pytest pytest`
- Run one file:
  - `uv run --with pytest pytest tests/test_pdf_crosswalk_parser.py`
- Run one test:
  - `uv run --with pytest pytest tests/test_transform_apply.py::test_apply_direct_missing_and_conditional_rules`
- Run with `-k` filter:
  - `uv run --with pytest pytest tests -k crosswalk`

### Fast CLI checks

- Convert synthetic fixture using ingested PDF rules:
  - `uv run python -m m2s3om_graph.cli.main demo-convert`
- Ingest authoritative PDF explicitly:
  - `uv run python -m m2s3om_graph.cli.main ingest-pdf --pdf /home/casas/AI/Metadata-Mappings/DataCite_DublinCore_Mapping.pdf`

## Coding conventions

### Imports

- Group imports: stdlib, third-party, local package imports.
- Prefer explicit imports; no wildcard imports.

### Formatting

- Follow PEP 8 defaults.
- Keep line length readable and use trailing commas for multiline literals/calls.

### Typing

- Use Python 3.12 hints (`list[str]`, `X | None`).
- Type all public functions and class methods.
- Avoid `Any` unless unavoidable at integration boundaries.

### Naming

- Functions/variables/modules: `snake_case`.
- Classes: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.

### Error handling

- Validate required config at startup boundaries.
- Raise explicit errors for invalid state.
- Avoid silently swallowing exceptions.

## Domain-specific guidance

- Preserve typed entities for metadata standards:
  - `Standard`, `Element`, `Definition`, `Example`, `Chunk`
  - `Crosswalk`, `MappingRecord`, `Citation`
- Keep retrieval grounded:
  - every mapping should carry citations (chunk IDs/URL anchors)
  - track ambiguity and semantic-loss flags
- Keep RAG Q&A scoped to standards/mappings corpus.

## Change workflow for agents

1. Prefer minimal, focused changes.
2. Add or update tests with behavior changes.
3. Run targeted tests first, then full tests.
4. Run lint and type checks for touched paths.
5. Note pre-existing warnings separately from newly introduced issues.
