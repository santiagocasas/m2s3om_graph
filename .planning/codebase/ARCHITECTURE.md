<!-- refreshed: 2026-05-08 -->
# Architecture

**Analysis Date:** 2026-05-08

## System Overview

```text
┌─────────────────────────────────────────────────────────────┐
│                      Presentation Layer                      │
├──────────────────┬──────────────────┬───────────────────────┤
│     Streamlit UI │   m2s3om_graph CLI   │    Testing Suite      │
│   `app/app.py`   │ `src/m2s3om_graph/cli` │    `tests/`           │
└────────┬─────────┴────────┬─────────┴──────────┬────────────┘
         │                  │                     │
         ▼                  ▼                     ▼
┌─────────────────────────────────────────────────────────────┐
│                       Domain Layer                          │
│     `src/m2s3om_graph/ingest`  `src/m2s3om_graph/transform`          │
│     `src/m2s3om_graph/rdamsc`  `src/m2s3om_graph/retrieval`          │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│  Persistence Layer (CrosswalkStore)                         │
│  `src/m2s3om_graph/db/crosswalk_repository.py`                  │
└─────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

| Component | Responsibility | File |
|-----------|----------------|------|
| CLI | Batch ingestion, syncing, and benchmarking | `src/m2s3om_graph/cli/main.py` |
| Web UI | Interactive browser and manual conversion | `app/app.py` |
| Ingest | Parsing PDFs and API data into DB records | `src/m2s3om_graph/ingest/` |
| Transform | Applying mapping rules to records via IR | `src/m2s3om_graph/transform/` |
| RDAMSC | Domain-specific pipelines for RDAMSC crosswalks | `src/m2s3om_graph/rdamsc/` |
| Store | Abstract interface for metadata persistence | `src/m2s3om_graph/db/crosswalk_repository.py` |
| Retrieval | RAG-based candidate mapping suggestions | `src/m2s3om_graph/retrieval/` |

## Pattern Overview

**Overall:** Layered Architecture with Repository Pattern.

**Key Characteristics:**
- **Separation of Concerns:** Strict boundary between the persistence layer (`CrosswalkStore`) and domain logic.
- **Intermediate Representation (IR):** Transformation doesn't go directly from source to target; it uses an IR (`src/m2s3om_graph/transform/ir.py`) for flexibility and debugging.
- **Evidence-Based:** Every mapping rule is linked to `Evidence` (chunks of documents), ensuring traceability.

## Layers

**Presentation:**
- Purpose: Provide user interfaces for system interaction.
- Location: `app/` and `src/m2s3om_graph/cli/`
- Contains: Streamlit views, argparse CLI handlers.
- Depends on: Domain Layer.
- Used by: End users.

**Domain:**
- Purpose: Implement core business logic for metadata mapping.
- Location: `src/m2s3om_graph/`
- Contains: Ingestion parsers, transformation engine, RAG retrieval.
- Depends on: Persistence Layer.
- Used by: Presentation Layer.

**Persistence:**
- Purpose: Abstract and implement storage of metadata standards and crosswalks.
- Location: `src/m2s3om_graph/db/`
- Contains: SurrealDB implementation, In-memory implementation, Pydantic models.
- Depends on: SurrealDB (external).
- Used by: Domain Layer.

## Data Flow

### Primary Request Path (Transformation)

1. **Source Record** is provided (UI or CLI) (`app/views/transform.py` or `src/m2s3om_graph/cli/main.py`).
2. **Crosswalk Bundle** is retrieved from store (`src/m2s3om_graph/db/crosswalk_repository.py`).
3. **Transform Engine** applies rules to generate Target IR (`src/m2s3om_graph/transform/apply.py`).
4. **Serializer** converts IR to final format (e.g., XML) (`src/m2s3om_graph/transform/serializers.py`).

### Ingestion Path

1. **Source Document** (PDF/JSON) is processed by an ingester (`src/m2s3om_graph/ingest/`).
2. **Records** (Standards, Elements, Rules) are created/updated in the store.
3. **Evidence** (Chunks) are linked to rules for traceability.

**State Management:**
- UI state is managed by Streamlit session state (`app/state.py`).
- Persistence is managed via SurrealDB.

## Key Abstractions

**CrosswalkBundle:**
- Purpose: A cohesive unit containing a crosswalk, its source/target standards, and all associated rules and evidence.
- Examples: `src/m2s3om_graph/db/crosswalk_repository.py`
- Pattern: Data Transfer Object (DTO).

**MappingRule:**
- Purpose: Defines how a source element maps to a target element, including conditions and transformations.
- Examples: `src/m2s3om_graph/db/models.py`
- Pattern: Rule-based engine.

**IRValue:**
- Purpose: Represents a value in a generic "Intermediate Representation" during transformation.
- Examples: `src/m2s3om_graph/transform/ir.py`
- Pattern: Value Object.

## Entry Points

**CLI:**
- Location: `src/m2s3om_graph/cli/main.py`
- Triggers: Shell commands (e.g., `uv run python -m m2s3om_graph.cli.main ingest-pdf`).
- Responsibilities: Batch processing, system maintenance, benchmarking.

**Web UI:**
- Location: `app/app.py`
- Triggers: Browser access (Streamlit).
- Responsibilities: Interactive exploration, manual pipeline runs, single-record conversion.

## Architectural Constraints

- **Threading:** Primarily single-threaded event loop (Streamlit/CLI).
- **Global state:** Minimal; persistence is handled via the `CrosswalkStore` instance.
- **Circular imports:** Avoided by using a clear layered dependency graph (Presentation -> Domain -> Persistence).

## Anti-Patterns

### Direct DB Access in UI
**What happens:** UI views calling SurrealDB queries directly.
**Why it's wrong:** Bypasses the `CrosswalkStore` abstraction, making the system hard to test or migrate.
**Do this instead:** Always use `CrosswalkStore` methods (`src/m2s3om_graph/db/crosswalk_repository.py`).

## Error Handling

**Strategy:** Explicit exception raising with domain-specific error types.

**Patterns:**
- Custom error classes in `src/m2s3om_graph/errors.py`.
- Validation at boundaries (e.g., checking if PDF exists before ingestion).

## Cross-Cutting Concerns

**Logging:** Standard python logging and print statements for CLI verbose mode.
**Validation:** Pydantic models in `src/m2s3om_graph/db/models.py` for data integrity.
**Authentication:** DB authentication handled via environment variables in `src/m2s3om_graph/db/crosswalk_repository.py`.

---

*Architecture analysis: 2026-05-08*
