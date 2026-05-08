---
phase: 01-rename
plan: 01
type: execute
wave: 1
depends_on: []
files_modified: []
autonomous: true
requirements:
  - rename-package
user_setup: []
---

# Phase 01: Project Rename — Execution Plan

## Objective

Execute a comprehensive rename of all "m2s3om_graph" references to "m2s3om_graph" across the entire codebase in a single atomic commit.

**Purpose:** The codebase currently uses "m2s3om_graph" as the package name and namespace. This plan renames it to "m2s3om_graph" for consistency with the project's actual identity. This is a one-time refactor that must be done cleanly to avoid broken imports and runtime errors.

**Output:** A fully renamed codebase where:
- All source files import from `m2s3om_graph.*` instead of `m2s3om_graph.*`
- Package metadata (`pyproject.toml`) updated
- CLI command updated from `m2s3om_graph` to `m2s3om_graph`
- Environment variable prefixes updated from `M2S3OM_*` to `M2S3OM_*`
- Container/service names updated
- All tests passing

---

## Execution Context

- **Phase Directory:** `.planning/phases/01-rename/`
- **Reference Document:** `.planning/discuss/DISCUSS.md`
- **Previous State:** Package named `m2s3om_graph` with directory `src/m2s3om_graph/`
- **Target State:** Package named `m2s3om_graph` with directory `src/m2s3om_graph/`

---

## Context

@.planning/discuss/DISCUSS.md
@.planning/PROJECT.md
@.planning/ROADMAP.md

---

## Tasks

### Task 1: Rename package directory

**Files:** `src/m2s3om_graph/` → `src/m2s3om_graph/`

**Action:** Rename the entire source directory from `m2s3om_graph` to `m2s3om_graph`:

```bash
mv src/m2s3om_graph src/m2s3om_graph
```

This is the foundational change. All subsequent tasks update references to this new path.

**Verify:**
```bash
ls -la src/m2s3om_graph/
ls -la src/m2s3om_graph/  # should not exist
```

**Done:** Directory `src/m2s3om_graph/` exists with all subdirectories and files intact.

---

### Task 2: Update imports in all Python files

**Files:** All `.py` files in `src/m2s3om_graph/`, `app/`, `tests/`, `scripts/`

**Action:** Replace all import statements from `m2s3om_graph` to `m2s3om_graph`:

```bash
# Replace 'from m2s3om_graph.' imports
find . -name "*.py" -type f -exec sed -i 's/from m2s3om_graph\./from m2s3om_graph./g' {} +

# Replace 'import m2s3om_graph' statements
find . -name "*.py" -type f -exec sed -i 's/import m2s3om_graph/import m2s3om_graph/g' {} +
```

**Verify:**
```bash
grep -r "from m2s3om_graph\." . --include="*.py"  # should return nothing
grep -r "import m2s3om_graph" . --include="*.py"  # should return nothing
```

**Done:** All Python files import from `m2s3om_graph.*` and `import m2s3om_graph` where needed.

---

### Task 3: Update package metadata in pyproject.toml

**Files:** `pyproject.toml`

**Action:** Edit `pyproject.toml` to update:
- Package name: `name = "m2s3om_graph"` → `name = "m2s3om_graph"`
- Wheel packages path: `packages = ["src/m2s3om_graph"]` → `packages = ["src/m2s3om_graph"]`
- CLI entrypoint: `m2s3om_graph = ...` → `m2s3om_graph = ...`

**Done:** `pyproject.toml` contains:
```toml
[project]
name = "m2s3om_graph"
...

[tool.hatch.build.targets.wheel]
packages = ["src/m2s3om_graph"]

[project.scripts]
m2s3om_graph = "m2s3om_graph.cli.main:main"
```

---

### Task 4: Update environment variable constants

**Files:** `src/m2s3om_graph/config/settings.py`, `src/m2s3om_graph/db/crosswalk_repository.py`, `src/m2s3om_graph/sssom.py`, `app/app.py`, `app/state.py`, `app/views/system.py`

**Action:** Replace `M2S3OM_*` with `M2S3OM_*`:

```bash
# Environment variable defaults in settings
sed -i 's/M2S3OM_DB_URL/M2S3OM_DB_URL/g' src/m2s3om_graph/config/settings.py
sed -i 's/M2S3OM_DB_NS/M2S3OM_DB_NS/g' src/m2s3om_graph/config/settings.py
sed -i 's/M2S3OM_DB_NAME/M2S3OM_DB_NAME/g' src/m2s3om_graph/config/settings.py
sed -i 's/M2S3OM_DB_USER/M2S3OM_DB_USER/g' src/m2s3om_graph/config/settings.py
sed -i 's/M2S3OM_DB_PASSWORD/M2S3OM_DB_PASSWORD/g' src/m2s3om_graph/config/settings.py
sed -i 's/M2S3OM_LLM_MODEL/M2S3OM_LLM_MODEL/g' src/m2s3om_graph/config/settings.py
sed -i 's/M2S3OM_EMBEDDINGS_MODEL/M2S3OM_EMBEDDINGS_MODEL/g' src/m2s3om_graph/config/settings.py
sed -i 's/M2S3OM_RETRIEVAL_TOP_K/M2S3OM_RETRIEVAL_TOP_K/g' src/m2s3om_graph/config/settings.py

# Update DB default values (namespace)
sed -i 's/"m2s3om_graph"/"m2s3om_graph"/g' src/m2s3om_graph/config/settings.py
sed -i 's/"m2s3om_graph"/"m2s3om_graph"/g' src/m2s3om_graph/db/crosswalk_repository.py

# Update local base URL
sed -i 's/m2s3om_graph.local/m2s3om_graph.local/g' src/m2s3om_graph/sssom.py
sed -i 's/_m2s3om_graph/_m2s3om_graph/g' src/m2s3om_graph/sssom.py
sed -i 's/m2s3om_graph:/m2s3om_graph:/g' src/m2s3om_graph/sssom.py
```

**Done:** All environment variable references use `M2S3OM_*` prefix and default namespace is `m2s3om_graph`.

---

### Task 5: Update CLI description

**Files:** `src/m2s3om_graph/cli/main.py`

**Action:** Update the CLI argument parser description:

```bash
sed -i 's/description="m2s3om_graph CLI"/description="m2s3om_graph CLI"/g' src/m2s3om_graph/cli/main.py
```

**Done:** `app = argparse.ArgumentParser(description="m2s3om_graph CLI")`

---

### Task 6: Update scripts

**Files:** `scripts/run_surrealdb_local.sh`, `scripts/run_app_local.sh`, `scripts/helpers/wait_surreal_ready.py`

**Action:**
1. Update container name:
```bash
sed -i 's/m2s3om_graph-surrealdb/m2s3om_graph-surrealdb/g' scripts/run_surrealdb_local.sh
```

2. Update volume mount paths:
```bash
sed -i 's|/dbs/m2s3om_graph|/dbs/m2s3om_graph|g' scripts/run_surrealdb_local.sh
```

3. Update wait script import:
```bash
sed -i 's/from m2s3om_graph.db.surreal_health/from m2s3om_graph.db.surreal_health/g' scripts/helpers/wait_surreal_ready.py
```

4. Update imports in all scripts:
```bash
sed -i 's/from m2s3om_graph\./from m2s3om_graph./g' scripts/*.py
```

5. Update env var references in shell scripts:
```bash
sed -i 's/M2S3OM/M2S3OM/g' scripts/run_surrealdb_local.sh scripts/run_app_local.sh
```

**Done:** All scripts reference `m2s3om_graph` in container names, paths, and imports.

---

### Task 7: Update README.md and documentation

**Files:** `README.md`, `CODEBASE_WALKTHROUGH.md`

**Action:**
```bash
# README.md - package name and imports
sed -i 's/`m2s3om_graph`/`m2s3om_graph`/g' README.md
sed -i 's/m2s3om_graph CLI/m2s3om_graph CLI/g' README.md
sed -i 's/m2s3om_graph-surrealdb/m2s3om_graph-surrealdb/g' README.md
sed -i 's/M2S3OM_/M2S3OM_/g' README.md

# Update directory references in README
sed -i 's/src\/m2s3om_graph\//src\/m2s3om_graph\//g' README.md

# CODEBASE_WALKTHROUGH.md
sed -i 's/m2s3om_graph/m2s3om_graph/g' CODEBASE_WALKTHROUGH.md
sed -i 's/Codebase: Complete Linear Walkthrough/Codebase: Complete Linear Walkthrough/g' CODEBASE_WALKTHROUGH.md
```

**Done:** README.md and CODEBASE_WALKTHROUGH.md reflect `m2s3om_graph` throughout.

---

### Task 8: Update app metadata

**Files:** `app/app.py`, `app/state.py`

**Action:**
```bash
# Page title
sed -i 's/page_title="m2s3om_graph crosswalks"/page_title="m2s3om_graph crosswalks"/g' app/app.py

# Environment variable defaults
sed -i 's/"m2s3om_graph"/"m2s3om_graph"/g' app/views/system.py
sed -i 's/m2s3om_graph:/m2s3om_graph:/g' app/state.py
```

**Done:** Streamlit app uses `m2s3om_graph` in page title and namespace references.

---

### Task 9: Update test files

**Files:** All test files in `tests/`

**Action:** Replace all import paths in tests:
```bash
find tests/ -name "*.py" -type f -exec sed -i 's/from m2s3om_graph\./from m2s3om_graph./g' {} +
find tests/ -name "*.py" -type f -exec sed -i 's/import m2s3om_graph/import m2s3om_graph/g' {} +
find tests/ -name "*.py" -type f -exec sed -i 's/m2s3om_graph\./m2s3om_graph./g' {} +
```

**Done:** All test files import from `m2s3om_graph.*` and reference new paths.

---

### Task 10: Run full test suite

**Files:** N/A

**Action:** Sync dependencies and run tests:
```bash
uv sync
uv run --with pytest pytest
```

**Verify:** All tests pass:
```bash
uv run --with pytest pytest
```

**Done:** All 100+ tests pass with the renamed package.

---

## Rollback Plan

If the rename fails or causes critical issues:

1. **Restore from git:**
   ```bash
   git status
   git diff
   # If changes look wrong, discard:
   git restore .
   ```

2. **If already committed:**
   ```bash
   git log --oneline -5
   git reset --hard HEAD~1
   ```

3. **Local cleanup (if needed):**
   ```bash
   rm -rf build/ dist/ *.egg-info/
   uv sync
   ```

**Note:** This is a local-only rename. No external deployments or databases are involved.

---

## Verification Steps

After completing all tasks:

1. **Verify directory rename:**
   ```bash
   ls -la src/m2s3om_graph/
   test -d src/m2s3om_graph && echo "ERROR: old directory still exists" || echo "OK"
   ```

2. **Verify no m2s3om_graph imports remain:**
   ```bash
   grep -r "from m2s3om_graph\." . --include="*.py" && echo "FAIL: found m2s3om_graph imports" || echo "OK"
   grep -r "import m2s3om_graph" . --include="*.py" && echo "FAIL: found m2s3om_graph imports" || echo "OK"
   ```

3. **Verify no m2s3om_graph.db namespace in SSSOM:**
   ```bash
   grep -r "m2s3om_graph:" src/ --include="*.py" && echo "FAIL: found m2s3om_graph namespace" || echo "OK"
   ```

4. **Run full test suite:**
   ```bash
   uv sync
   uv run --with pytest pytest -v
   ```

5. **Test CLI:**
   ```bash
   uv build
   uv run m2s3om_graph demo-convert
   ```

---

## Success Criteria

- [ ] `src/m2s3om_graph/` renamed to `src/m2s3om_graph/`
- [ ] All `from m2s3om_graph.*` imports → `from m2s3om_graph.*`
- [ ] All `import m2s3om_graph` → `import m2s3om_graph`
- [ ] `pyproject.toml` package name = "m2s3om_graph"
- [ ] CLI command = `m2s3om_graph`
- [ ] All `M2S3OM_*` env vars → `M2S3OM_*`
- [ ] Container name = `m2s3om_graph-surrealdb`
- [ ] All tests pass (`uv run --with pytest pytest`)
- [ ] CLI works (`uv run m2s3om_graph demo-convert`)

---

## Output

After completion, create:
- `.planning/phases/01-rename/01-PLAN-SUMMARY.md`
