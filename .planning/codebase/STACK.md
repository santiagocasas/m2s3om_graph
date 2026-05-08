# Technology Stack

**Analysis Date:** 2026-05-08

## Languages

**Primary:**
- Python 3.12+ - Main application logic, data processing, and CLI `src/m2s3om_graph/`

**Secondary:**
- SurQL - SurrealDB query language used for schema and data operations `src/m2s3om_graph/db/surreal_schema.py`

## Runtime

**Environment:**
- Python 3.12

**Package Manager:**
- uv
- Lockfile: present (`uv.lock`)

## Frameworks

**Core:**
- Pydantic 2.11.0 - Data validation and settings management `src/m2s3om_graph/db/models.py`
- SurrealDB 1.0.4 - Graph database for storing metadata standards and crosswalks `src/m2s3om_graph/db/crosswalk_repository.py`
- Streamlit 1.43.0 - Web-based workbench UI `app/app.py`

**Testing:**
- pytest 8.3.0 - Unit and integration testing `tests/`

**Build/Dev:**
- Hatchling 1.27.0 - Build backend `pyproject.toml`
- Ruff 0.11.0 - Linting and formatting
- BasedPyright 1.28.0 - Static type checking

## Key Dependencies

**Critical:**
- pypdf 5.4.0 - PDF parsing for crosswalk ingestion `src/m2s3om_graph/ingest/pdf_crosswalk_parser.py`
- markitdown 0.1.0 - Document conversion to markdown `pyproject.toml`
- requests 2.32.0 - HTTP client for external data fetching `src/m2s3om_graph/interop/elib.py`

**Infrastructure:**
- PyYAML 6.0.2 - YAML configuration and data parsing `src/m2s3om_graph/sssom.py`
- Matplotlib 3.10.8 - Data visualization `pyproject.toml`

## Configuration

**Environment:**
- Configured via environment variables accessed through `os.getenv`.
- Key configs required for database connectivity (e.g., `M2S3OM_DB_URL`).

**Build:**
- `pyproject.toml` defines project metadata, dependencies, and build targets.

## Platform Requirements

**Development:**
- Python 3.12+
- uv package manager

**Production:**
- SurrealDB instance (accessible via WebSocket/HTTP)
- Streamlit hosting environment

---

*Stack analysis: 2026-05-08*
