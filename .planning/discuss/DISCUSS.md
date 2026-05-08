# Phase 1: Project Setup & Rename — Discussion

## Overview

This document captures the discussion and planning for renaming the codebase from `m2s3om_graph` to `m2s3om_graph`.

## Current State

### Package Name
- **Current:** `m2s3om_graph`
- **Proposed:** `m2s3om_graph`
- **Impact:** Package metadata (`pyproject.toml`), directory structure, imports

### Scope of Changes

#### 1. Directory Structure
```
src/m2s3om_graph/              → src/m2s3om_graph/
src/m2s3om_graph/rdamsc/       → src/m2s3om_graph/rdamsc/
src/m2s3om_graph/transform/    → src/m2s3om_graph/transform/
src/m2s3om_graph/db/           → src/m2s3om_graph/db/
src/m2s3om_graph/ingest/       → src/m2s3om_graph/ingest/
src/m2s3om_graph/sssom.py      → src/m2s3om_graph/sssom.py
src/m2s3om_graph/cli/main.py   → src/m2s3om_graph/cli/main.py
# etc. for all submodules
```

#### 2. Package Metadata (`pyproject.toml`)
```toml
[project]
name = "m2s3om_graph"                    → name = "m2s3om_graph"
description = "Metadata crosswalk..." → (keep as-is, no name reference)

[project.scripts]
m2s3om_graph = "m2s3om_graph.cli.main:main"  → m2s3om_graph = "m2s3om_graph.cli.main:main"

[tool.hatch.build.targets.wheel]
packages = ["src/m2s3om_graph"]          → packages = ["src/m2s3om_graph"]
```

#### 3. Module Imports
All `m2s3om_graph.*` imports → `m2s3om_graph.*`:
- `from m2s3om_graph.db import ...` → `from m2s3om_graph.db import ...`
- `from m2s3om_graph.cli.main import ...` → `from m2s3om_graph.cli.main import ...`
- `import m2s3om_graph` → `import m2s3om_graph`

#### 4. Constants and Variables
```python
M2S3OM_DB_NS = "m2s3om_graph"          → M2S3OM_DB_NS = "m2s3om_graph"
M2S3OM_LOCAL_BASE_URL              → M2S3OM_LOCAL_BASE_URL
M2S3OM_DB_WAIT_*                   → M2S3OM_DB_WAIT_*
```

#### 5. CLI Description
```python
parser = argparse.ArgumentParser(description="m2s3om_graph CLI")  # → "m2s3om_graph CLI"
```

#### 6. Database/Container Names
- Container: `m2s3om_graph-surrealdb` → `m2s3om_graph-surrealdb`
- DB namespace: `m2s3om_graph` → `m2s3om_graph`
- Volume mount: `/dbs/m2s3om_graph` → `/dbs/m2s3om_graph`

#### 7. Documentation and Comments
- README.md: All references to `m2s3om_graph`
- Inline comments
- Docstrings
- Script names/paths

#### 8. Tests
- Import paths in test files
- Test fixtures referencing `m2s3om_graph`
- Mocked URLs/paths

#### 9. Build Artifacts
- `uv.lock`: Package name entry
- Build cache cleanup required

## Questions

### 1. Naming Consistency
**Q:** Should the package name be `m2s3om_graph` or `m2s3om`?
- `m2s3om_graph` is more descriptive and matches current project identity
- **Recommendation:** Keep `m2s3om_graph` (full name)

### 2. Backward Compatibility
**Q:** Should we maintain backward compatibility during the rename?
- This appears to be an internal project rename (early stage)
- **Recommendation:** Full rename, no backward compatibility layer

### 3. External Dependencies
**Q:** Are there external integrations or plugins that reference `m2s3om_graph`?
- No evidence of external plugins found
- CLI script name change may affect user workflows
- **Recommendation:** Document the script name change in release notes

### 4. Database Namespace
**Q:** Should the database namespace change from `m2s3om_graph` to `m2s3om_graph`?
- Existing data in `m2s3om_graph` namespace will need migration or be orphaned
- New installations will use `m2s3om_graph`
- **Recommendation:** Full rename for consistency

### 5. Base URLs
**Q:** Should `https://m2s3om_graph.local` → `https://m2s3om_graph.local`?
- This affects SSSOM mapping set IDs
- May impact existing mappings if URLs are used as identifiers
- **Recommendation:** Full rename for consistency

## Rename Strategy

### Phase 1: Codebase Rename (Immediate)
1. Rename `src/m2s3om_graph/` → `src/m2s3om_graph/`
2. Update all import statements
3. Update package metadata (`pyproject.toml`)
4. Update CLI script name
5. Update constants and variables
6. Update container/script names

### Phase 2: Documentation Updates
1. Update README.md
2. Update inline comments
3. Update docstrings
4. Update CI/CD scripts

### Phase 3: Testing & Verification
1. Run test suite
2. Verify CLI works
3. Verify Streamlit app
4. Verify imports in interactive mode

### Phase 4: Cleanup
1. Remove old `src/m2s3om_graph/` directory
2. Clean build cache (`rm -rf build/ dist/ *.egg-info/`)
3. Update `uv.lock`

## Execution Plan

### Step 1: Directory Rename
```bash
mv src/m2s3om_graph src/m2s3om_graph
```

### Step 2: Replace Import Statements
```bash
# Replace all import references
find . -name "*.py" -type f -exec sed -i 's/from m2s3om_graph\./from m2s3om_graph./g' {} +
find . -name "*.py" -type f -exec sed -i 's/import m2s3om_graph/import m2s3om_graph/g' {} +
```

### Step 3: Update Package Metadata
Edit `pyproject.toml`:
- `name = "m2s3om_graph"` → `name = "m2s3om_graph"`
- `[tool.hatch.build.targets.wheel] packages = ["src/m2s3om_graph"]`

### Step 4: Update CLI Script
- `[project.scripts] m2s3om_graph = ...` → `m2s3om_graph = ...`

### Step 5: Update Constants
Replace `M2S3OM_*` → `M2S3OM_*` in:
- `src/m2s3om_graph/config/settings.py`
- `src/m2s3om_graph/db/crosswalk_repository.py`
- `src/m2s3om_graph/sssom.py`

### Step 6: Update CLI Description
- `m2s3om_graph CLI` → `m2s3om_graph CLI`

### Step 7: Update Scripts
- `scripts/run_surrealdb_local.sh`
- `scripts/run_app_local.sh`
- `scripts/stop_surrealdb_local.sh`
- `scripts/rdamsc_pipeline_stats.py`
- `scripts/helpers/wait_surreal_ready.py`

### Step 8: Update Documentation
- README.md (multiple references)
- Inline comments
- Docstrings

### Step 9: Verify and Test
```bash
uv sync
uv run --with pytest pytest
uv run streamlit run app/app.py
uv run python -m m2s3om_graph.cli.main demo-convert
```

### Step 10: Cleanup
```bash
rm -rf build/ dist/ *.egg-info/
uv run --with ruff ruff check src app tests
uv run --with basedpyright basedpyright src
```

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Breaking existing imports | High | Automated replacement, thorough testing |
| Database migration needed | Medium | Document required migration steps |
| CLI script name change | Low | Document in release notes |
| External integrations broken | Low | No evidence of external dependencies |

## Recommended Approach

**Approach:** Full rename without backward compatibility

**Rationale:**
1. Project appears to be in early/staging phase
2. No evidence of external plugins or integrations
3. Full rename reduces technical debt and confusion
4. Can be done systematically with automated tools

**Next Step:** Proceed with `/gsd-plan-phase 1` to create executable plan
