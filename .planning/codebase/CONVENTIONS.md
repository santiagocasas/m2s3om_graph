# Coding Conventions

**Analysis Date:** 2026-05-08

## Naming Patterns

**Files:**
- Modules use `snake_case.py` (e.g., `src/m2s3om_graph/crosswalk/reverse.py`).

**Functions:**
- Public and private functions use `snake_case` (e.g., `make_error_payload` in `src/m2s3om_graph/errors.py`).

**Variables:**
- Local variables and attributes use `snake_case` (e.g., `source_url` in `src/m2s3om_graph/models/standards.py`).

**Types:**
- Classes use `PascalCase` (e.g., `Standard` in `src/m2s3om_graph/models/standards.py`).
- Constants use `UPPER_SNAKE_CASE` (as per `AGENTS.md`).

## Code Style

**Formatting:**
- Tool: `ruff` is used for both linting and formatting.
- Line length: Follows PEP 8 defaults with an emphasis on readability.

**Linting:**
- Tool: `ruff` and `basedpyright` for static type checking.
- Typing: Strict use of Python 3.12 type hints (e.g., `list[str]`, `X | None`). All public functions and class methods are typed.

## Import Organization

**Order:**
1. Standard library imports (e.g., `import json`, `from pathlib import Path`).
2. Third-party imports (e.g., `from pydantic import BaseModel`).
3. Local package imports (e.g., `from m2s3om_graph.db import build_default_store`).

**Path Aliases:**
- Absolute imports within the `m2s3om_graph` package are preferred (e.g., `from m2s3om_graph.errors import ...`).

## Error Handling

**Patterns:**
- Structured error reporting via `make_error_payload` in `src/m2s3om_graph/errors.py`, which returns a `TypedDict` (`ErrorPayload`) containing source, operation, error type, and message.
- Explicit errors are raised for invalid state; silently swallowing exceptions is avoided.

## Logging

**Framework:** Console output via `print` for CLI tools and reporting.

**Patterns:**
- CLI errors are prefixed with `error: ` (e.g., `print("error: expected mapping PDF missing")` in `src/m2s3om_graph/cli/main.py`).
- Verbose logging is implemented via optional logger functions passed to pipelines (e.g., `_logger_from_verbose` in `src/m2s3om_graph/cli/main.py`).

## Comments

**When to Comment:**
- Following PEP 8; documentation is primarily handled through type hints and clear naming.

**JSDoc/TSDoc:**
- Not applicable (Python codebase).

## Function Design

**Size:** Functions are kept focused; complex logic is delegated to helper functions.

**Parameters:** Keyword-only arguments are used for clarity in utility functions (e.g., `make_error_payload` in `src/m2s3om_graph/errors.py`).

**Return Values:** Return types are explicitly hinted (e.g., `-> ErrorPayload`).

## Module Design

**Exports:** Explicit imports are used; wildcard imports (`from ... import *`) are forbidden.

**Barrel Files:** `__init__.py` files are used for package organization but avoid heavy logic.

---

*Convention analysis: 2026-05-08*
