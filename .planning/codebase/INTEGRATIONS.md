# External Integrations

**Analysis Date:** 2026-05-08

## APIs & External Services

**Metadata Repositories:**
- elib.dlr.de - Used for fetching Dublin Core and OpenAire metadata exports.
  - SDK/Client: `requests`
  - Implementation: `src/m2s3om_graph/interop/elib.py`
  - Endpoints: Defined in `src/m2s3om_graph/interop/constants.py`

## Data Storage

**Databases:**
- SurrealDB (Graph Database)
  - Connection: `M2S3OM_DB_URL` (default: `ws://localhost:8000/rpc`)
  - Client: `surrealdb` Python SDK
  - Implementation: `src/m2s3om_graph/db/crosswalk_repository.py`

**File Storage:**
- Local filesystem for PDF ingestion and fixture files.

**Caching:**
- Not detected.

## Authentication & Identity

**Auth Provider:**
- Custom (SurrealDB Native)
  - Implementation: Username/password based authentication via `surrealdb` SDK in `src/m2s3om_graph/db/crosswalk_repository.py`.

## Monitoring & Observability

**Error Tracking:**
- Not detected.

**Logs:**
- Standard Python logging/exceptions.

## CI/CD & Deployment

**Hosting:**
- Streamlit (Application UI)

**CI Pipeline:**
- Not detected in codebase.

## Environment Configuration

**Required env vars:**
- `M2S3OM_USE_SURREAL`: Enable/disable SurrealDB backend (1/true/yes/on).
- `M2S3OM_DB_URL`: Connection string for SurrealDB.
- `M2S3OM_DB_USER`: Database username.
- `M2S3OM_DB_PASSWORD`: Database password.
- `M2S3OM_DB_NS`: SurrealDB namespace (default: `m2s3om_graph`).
- `M2S3OM_DB_NAME`: SurrealDB database name (default: `crosswalk`).

**Secrets location:**
- Expected to be provided via environment variables or `.env` file (not committed).

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

---

*Integration audit: 2026-05-08*
