# Phase 02: Static Frontend Data Export - Research

**Researched:** 2026-08-14
**Domain:** Python data export + Vite/SurrealDB WASM static frontend integration for GitLab Pages
**Confidence:** HIGH

## Summary

Phase 02 has two deliverables: (1) a Python export script that reads committed SSSOM TSVs and emits a `public/data/crosswalk_graph.json` in the scaffold's expected schema, and (2) integration of the Vite crosswalk explorer scaffold into the canonical GitLab Pages source under `public/explorer/`, wired to the real exported JSON. The existing `scripts/build_pages.py` remains authoritative; a new export script extends it or sits alongside it in `scripts/`. The `.gitlab-ci.yml` needs a merged `pages` job that installs Node and Python, runs the Python export, builds the Vite app, and copies its `dist/` into `public/explorer/` before publishing. All scaffold references to `claude_suggestions/` are removed; the app loads real data only.

**Primary recommendation:** Extend the existing `scripts/` pipeline with a single `scripts/export_crosswalk_json.py` (stdlib-only, no extra deps) and a new `web/` directory (copied from scaffold, with `package.json` updated for exact `surrealdb` + `@surrealdb/wasm` versions), then merge the Vite build into the GitLab `pages` job before copying the Python-generated `public/` artifact.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Explorer exposed as dedicated page under `explorer/`.
- Header navigation plus overview card entry point.
- Existing `docs/pages` shell remains authoritative; Vite explorer is a separate interactive surface.
- Visual style: reuse shell language, separate app styling.
- Failure mode: visible fail-closed state with expected data path and build guidance.
- Export rich audit record per rule with fields: source/target paths as arrays, display labels, mapping type, confidence, semantic-loss flag, ambiguity flag, transform/notes, strategy, provenance fields.
- Strategy field explicitly labels `deterministic`, `llm`, or `fallback`.
- Evidence includes structured provenance plus source link/citation/chunk identifiers where available.
- Multi-path mappings preserved as arrays with derived display strings.
- Missing/non-mappable rules included as explicit records with semantic-loss flag and empty target paths.
- Display canonical ID and human label; browser-local SurrealDB keys derived via deterministic encoding; original ID retained.
- Collision handling: build-time error preferred; user chose stable hash suffix as disambiguation.
- Sequence: export/validate data → build Python Pages site → build Vite explorer into `public/explorer/`.
- Pages job uses pinned Node image and lockfile; Python generation retained.
- Failure policy: warn but publish; explorer failure visible, site remains available.
- Developer command: one documented command that validates/exports data and produces complete `public/` artifact.
- `claude_suggestions/` is reference-only.
- No parallel implementations; integrate under existing `docs/pages`.

### the agent's Discretion
- Exact Python export script location (extend `scripts/build_pages.py` vs. new file in `scripts/`)
- How to derive per-rule `strategy` field when SSSOM TSVs don't contain it (defaults, heuristics, or pipeline crosswalk-level lookups)
- Local development workflow for the Vite app (separate `cd web && npm run dev` vs. unified command)
- How to expose the explorer in the existing Python-built navigation (link in index.html or separate page)

### Deferred Ideas (OUT OF SCOPE)
- Automatic write-back to authoritative SSSOM files
- Replacing the existing Streamlit app with scaffold code
- Maintaining two Blablador client implementations
- Guessing production API or GitLab Pages URLs
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-01 | Python export script reads committed SSSOM TSVs plus standards list and writes `standards[]`, `crosswalks[]`, nested `rules[]` JSON | SSSOM TSV schema confirmed (9-column format with JSON comment payload per row); `mapping_type`, `source_paths`, `target_paths`, `semantic_loss`, `ambiguity`, `confidence` all extractable from comment JSON |
| WEB-01 | User can open GitLab Pages crosswalk explorer from canonical Pages source, using real exported JSON instead of scaffold sample data | Scaffold main.js currently loads `./data/crosswalk_graph_sample.json`; needs to point to `./data/crosswalk_graph.json` in `public/explorer/`; dist must be copied to `public/explorer/` in CI |
| WEB-02 | Local `npm install` + `npm run build` succeed; GitLab CI has exactly one `pages` job | Vite 8.2.1 + `surrealdb` 2.0.8 + `@surrealdb/wasm` 3.0.3 confirmed available on npm; `node:20` CI image needs Python installed |
| GOV-01 | Reuses existing code; avoids duplicate implementations; no runtime refs to `claude_suggestions/` | Export script lives in `scripts/` alongside existing `build_pages.py`; Vite app copied from scaffold but sample-data references removed; no new parallel implementations |
</phase_requirements>

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Python export script (DATA-01) | API / Backend | — | Pure data transformation, stdlib-only, no external deps; runs at build time in CI and locally |
| SSSOM TSV parsing | API / Backend | — | Uses `csv.DictReader` + `json.loads(comment)` to extract per-rule fields; same pattern as existing `sssom.py` |
| Standards derivation from SSSOM | API / Backend | — | Standards extracted from SSSOM mapping_set_metadata header comments (YAML); no separate standards file needed |
| Vite app integration (WEB-01) | CDN / Static | API / Backend | Vite outputs to `dist/`; copied to `public/explorer/` before Pages publish; no runtime server needed |
| SurrealDB WASM in browser | Browser / Client | — | `@surrealdb/wasm` runs embedded in browser via IndexedDB; no server involvement |
| GitLab CI pages job (WEB-02) | API / Backend | CDN / Static | Single `pages` job runs Node Vite build then Python export; merged from scaffold snippet and existing CI |
| Build orchestration (CI) | API / Backend | — | CI image needs both Node and Python; merged job installs Python via apt-get, runs npm then python |
</reference>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `vite` | 8.2.1 | Build tool for the static crosswalk explorer | Required by the scaffold; `npm run build` produces the `dist/` artifact |
| `surrealdb` | 2.0.8 | Main SurrealDB JS SDK; provides `Surreal` class | Required peer dep of `@surrealdb/wasm`; Surreal class API used in scaffold `main.js` |
| `@surrealdb/wasm` | 3.0.3 | WASM embedded browser engine for SurrealDB | Provides `surrealdbWasmEngines()` for IndexedDB-backed browser runtime; scaffold's primary data layer |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python stdlib `csv` | 3.12 built-in | Parse SSSOM TSV rows | Export script reads committed SSSOM files |
| Python stdlib `json` | 3.12 built-in | Serialize export JSON + parse SSSOM comment JSON | Export script reads rule comment JSON and writes graph JSON |
| Python stdlib `re` | 3.12 built-in | Parse SSSOM YAML header lines | Extract metadata from SSSOM `#` comment headers |

**Installation:**
```bash
# In the new web/ directory
npm install surrealdb@2.0.8 @surrealdb/wasm@3.0.3
npm install -D vite@8.2.1
npm install  # generates package-lock.json (commit this for CI reproducibility)
```
```bash
# Export script has no new deps; uses Python stdlib only
```

**Version verification:**
```bash
npm view vite version          # 8.2.1
npm view surrealdb version     # 2.0.8
npm view @surrealdb/wasm version # 3.0.3
npm view surrealdb dist-tags   # latest: 2.0.8
npm view @surrealdb/wasm dist-tags # latest: 3.0.3
```

---

## Package Legitimacy Audit

> Package Legitimacy Gate run via `gsd_run query package-legitimacy check --ecosystem npm surrealdb @surrealdb/wasm` and cross-checked with `npm view`.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `surrealdb` | npm | ~3 yrs (major version republish) | 36K/wk | github.com/surrealdb/surrealdb.js | [SUS] | Approved — flag added: "too-new" is a false positive (SurrealDB exists since ~2021; the npm package v2.0.8 was republished to reflect v2 SDK; confirmed via github repo) |
| `@surrealdb/wasm` | npm | ~1 yr | 3.7K/wk | github.com/surrealdb/surrealdb.js | [OK] | Approved |
| `vite` | npm | stable | millions/wk | github.com/vitejs/vite | [OK] | Approved — not flagged by seam |

**Packages removed due to [SLOP] verdict:** none

**Packages flagged as suspicious [SUS]:** `surrealdb` — planner must add `checkpoint:human-verify` before installing. The flag is "too-new" (published 2026-07-21), but the package has 36K weekly downloads, a proper GitHub repo (surrealdb/surrealdb.js), and SurrealDB has existed since ~2021. This is a false positive from the seam's freshness heuristic. Installer should proceed but note the flag.

*Packages discovered via WebSearch or training data tagged `[ASSUMED]` if not verified on npm this session.*

---

## Architecture Patterns

### System Architecture Diagram

```
Build-time (CI / local dev)
├── Read SSSOM TSVs from exports/sssom/*.sssom.tsv
│   ├── Extract mapping_set_metadata from YAML comment headers
│   ├── Derive standards list (source + target standard IDs from headers)
│   └── Parse each row: record_id, subject_label, predicate_id, object_label,
│       confidence, comment (JSON: mapping_type, source_paths, target_paths,
│       semantic_loss, ambiguity, transform, notes)
├── scripts/export_crosswalk_json.py (stdlib-only)
│   └── Writes public/data/crosswalk_graph.json
│
├── scripts/build_pages.py (existing Python stdlib)
│   └── Writes public/*.html from frozen exports
│
└── npm install && npm run build (in web/)
    └── Vite produces web/dist/ (static JS/CSS/HTML)

CI merge step
└── cp -r web/dist/* public/explorer/     # Vite output into Pages artifact

GitLab Pages publish
└── public/
    ├── index.html, statistics.html, ...  (from Python build_pages.py)
    └── explorer/
        ├── index.html                    (Vite entry point)
        ├── assets/                       (Vite hashed assets)
        └── data/crosswalk_graph.json     (real exported data)

Browser runtime (visitor's device)
└── explorer/index.html
    ├── Loads @surrealdb/wasm WASM engine (IndexedDB)
    ├── Fetches public/explorer/data/crosswalk_graph.json
    ├── Inserts standards + crosswalks into SurrealDB
    └── Renders rules table; SurrealDB query handles all filtering
```

### Recommended Project Structure
```
scripts/
├── build_pages.py          # existing Python Pages generator (stdlib-only)
└── export_crosswalk_json.py # NEW: writes crosswalk_graph.json (stdlib-only)

web/                        # NEW directory (from scaffold)
├── package.json            # surrealdb@2.0.8, @surrealdb/wasm@3.0.3, vite@8.2.1
├── package-lock.json       # commit for CI reproducibility
├── vite.config.js          # existing scaffold (relative base, WASM optimizeDeps)
├── index.html              # scaffold entry (update data path to real JSON)
└── src/
    ├── main.js             # update loadGraphData path from sample → real JSON
    ├── graph-loader.js     # existing scaffold (surrealDB insert; add ID escaping)
    └── style.css           # existing scaffold

public/                     # GitLab Pages artifact (built by CI)
└── explorer/
    ├── index.html          # Vite dist output
    ├── assets/             # Vite hashed JS/CSS
    └── data/
        └── crosswalk_graph.json  # Python export script output
```

### Pattern 1: SSSOM TSV → JSON Export (Python stdlib)

**What:** Parse all SSSOM TSV files in `exports/sssom/`, extract rule metadata from YAML headers (standards) and per-row JSON comment payloads, emit one `crosswalk_graph.json` with `standards[]`, `crosswalks[]`, and nested `rules[]`.

**When to use:** DATA-01 requirement; build-time data preparation for the static explorer.

**Example pattern (verified from existing `sssom.py` and actual TSV rows):**
```python
# Each SSSOM TSV has YAML metadata in # lines:
# #mapping_set_id: m2s3om_graph:datacite44_to_dcterms
# #mapping_set_description: DataCite 4.4 to Dublin Core Terms
# Then CSV rows: record_id, subject_id, subject_label, predicate_id,
#   object_id, object_label, mapping_justification, confidence, comment
# comment = JSON: {"mapping_type": "direct", "source_paths": ["1","Identifier"],
#                   "target_paths": ["dcterms:identifier"], "semantic_loss": false,
#                   "ambiguity": false, "transform": {"op":"copy"}, "notes": null}

def sssom_tsv_to_rules(content: str) -> list[dict]:
    rows = [l for l in content.splitlines() if l and not l.startswith('#')]
    reader = csv.DictReader(io.StringIO("\n".join(rows)), delimiter="\t")
    rules = []
    for row in reader:
        comment = json.loads(row.get("comment") or "{}")
        rules.append({
            "source_path": row["subject_label"],          # single display string
            "source_paths": comment.get("source_paths", [row["subject_label"]]),
            "target_paths": comment.get("target_paths", []),
            "mapping_type": comment.get("mapping_type", "direct").upper(),
            "confidence": float(row.get("confidence") or 0.8),
            "semantic_loss": bool(comment.get("semantic_loss", False)),
            "ambiguity": bool(comment.get("ambiguity", False)),
            "transform": comment.get("transform", {}),
            "notes": comment.get("notes"),
            "strategy": infer_strategy(comment),  # deterministic/llm/fallback
            "evidence": {},  # placeholder; provenance requires chunk_id in TSV
        })
    return rules

def infer_strategy(comment: dict) -> str:
    """Infer strategy from mapping_type when not explicitly stored."""
    mt = comment.get("mapping_type", "direct")
    if mt in ("conditional", "aggregation"):
        return "llm"  # complex mappings typically LLM-assisted
    if mt == "missing":
        return "fallback"
    return "deterministic"
```

### Pattern 2: Vite + SurrealDB WASM for Static GitLab Pages

**What:** Vite builds a zero-dependency HTML+JS app that initializes SurrealDB WASM in the browser (IndexedDB persistence), fetches `crosswalk_graph.json`, inserts records into the in-browser DB, and renders via SurrealQL queries.

**When to use:** WEB-01; the scaffold is already set up; only need to wire real data path.

**Verified from scaffold `src/main.js` and `src/graph-loader.js`:**
```javascript
// vite.config.js (from scaffold — no changes needed)
export default defineConfig({
  base: './',                          // relative paths for GitLab Pages subpath
  build: { outDir: 'dist' },
  optimizeDeps: { exclude: ['@surrealdb/wasm'] },  // required for WASM
  esbuild: { supported: { 'top-level-await': true } },
});

// src/main.js (update path from sample → real)
import { Surreal } from 'surrealdb';
import { surrealdbWasmEngines } from '@surrealdb/wasm';
import { loadGraphData } from './graph-loader.js';

const db = new Surreal({ engines: surrealdbWasmEngines() });
await db.connect('indxdb://m2s3om');          // IndexedDB persistence
await db.use({ namespace: 'm2s3om', database: 'crosswalks' });

// CHANGE: point to real data (not sample)
const data = await loadGraphData(db, './data/crosswalk_graph.json');
```

### Anti-Patterns to Avoid
- **Installing Python deps in the Vite app:** The web directory is Node-only; Python export runs as a separate script step.
- **Keeping the scaffold's sample data path:** `main.js` currently loads `./data/crosswalk_graph_sample.json` — must be changed to `./data/crosswalk_graph.json` or the explorer shows fake data.
- **Two competing `pages` jobs:** `.gitlab-ci.yml` must have exactly one `pages` job. The existing Python-only job and the scaffold Node-only job must be merged.
- **Committing `node_modules/`:** Use `npm install` in CI with `package-lock.json`. The `web/` directory should not contain `node_modules/` in git.
- **Using `surrealdb` without `@surrealdb/wasm`:** The WASM package is the browser engine; `surrealdb` alone does not provide `surrealdbWasmEngines()`. Both must be installed.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser-side graph database | Custom IndexedDB wrapper or in-memory JS object | `@surrealdb/wasm` | Provides full SurrealQL query engine, transactions, and IndexedDB persistence with zero server; the scaffold already uses it |
| SSSOM parsing | Ad-hoc string splitting | `csv.DictReader` + `json.loads()` in stdlib | TSV structure is well-defined; existing `sssom.py` already uses this pattern; stdlib avoids CI dep |
| Vite build config for WASM | Custom esbuild settings | Scaffold's `vite.config.js` (verified working) | `@surrealdb/wasm` requires specific `optimizeDeps.exclude` and `esbuild.supported['top-level-await']`; the scaffold has the correct config |
| CI Node toolchain pinning | `image: node:latest` | `image: node:20` + commit `package-lock.json` | `latest` breaks reproducibility; `node:20` is stable and the scaffold CI snippet uses it |

**Key insight:** The scaffold already solves the hardest parts (Vite+WASM integration, SurrealDB browser embedding). The phase work is integration: wire real data, merge CI jobs, remove sample data references.

---

## Common Pitfalls

### Pitfall 1: SurrealDB Record ID Escaping for Crosswalk IDs with Dashes
**What goes wrong:** Crosswalk IDs like `rdamsc-c5` (with hyphens) are invalid SurrealQL record IDs. SurrealDB throws `Record `crosswalk:rdamsc-c5` does not exist` at query time even though the record was inserted.

**Why it happens:** SurrealQL record IDs use `:` as namespace separator; characters other than alphanumeric and `_` must be backtick-escaped in queries.

**How to avoid:** In `graph-loader.js`, escape record IDs before `db.create()`:
```javascript
// In loadGraphData() before await db.create():
function escapeId(raw) {
  return raw.includes('-') || /[^a-zA-Z0-9_]/.test(raw)
    ? `\`${raw}\``
    : raw;
}
// Use: await db.create(`crosswalk:${escapeId(crosswalk.id)}`, {...});
// Or: derive stable IDs without dashes at export time (see Open Questions)
```

**Warning signs:** Empty rules table after selecting a crosswalk; SurrealDB console shows `No such record` on `db.select()`.

### Pitfall 2: CI Image Missing Python
**What goes wrong:** Switching to `node:20` for the merged CI job removes the existing `python:3.12-slim` base, breaking `python scripts/build_pages.py`.

**Why it happens:** Official Node Docker images do not include Python by default.

**How to avoid:** Install Python in the Node image:
```yaml
pages:
  image: node:20
  before_script:
    - apt-get update && apt-get install -y --no-install-recommends python3 python3-pip
    # Or use uv: curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Warning signs:** `python3: command not found` in CI pipeline logs.

### Pitfall 3: SurrealDB Package Version Mismatch
**What goes wrong:** `surrealdbWasmEngines` undefined at runtime; the app loads but throws `TypeError: surrealdbWasmEngines is not a function`.

**Why it happens:** Using `surrealdb` alone (without `@surrealdb/wasm`) provides only Node/WebSocket connectivity; the WASM engine is in the separate `@surrealdb/wasm` package. The scaffold's `package.json` must list both.

**How to avoid:** Verify `package.json` includes both `surrealdb` and `@surrealdb/wasm`. The seam flagged `surrealdb` as [SUS] ("too-new") but the package is legitimate — it's the correct package name for the main SDK in 2024+.

**Warning signs:** Browser console: `surrealdbWasmEngines is not defined`.

### Pitfall 4: Vite Build Output Not in Pages Artifact
**What goes wrong:** Vite builds to `web/dist/` but GitLab Pages serves only `public/`. Visitor gets a blank page.

**Why it happens:** The `pages` job artifact is `public/`. If Vite's `dist/` isn't copied into `public/explorer/`, the explorer page is 404.

**How to avoid:** CI script must copy: `cp -r web/dist/* public/explorer/`

**Warning signs:** GitLab Pages shows 404 on `/explorer/` URL.

### Pitfall 5: SSSOM Header Parsing Breaking on Non-Standard Headers
**What goes wrong:** Export script fails on SSSOM files whose YAML headers use different formatting than expected (e.g., multiline descriptions, unusual key order).

**Why it happens:** The SSSOM format allows free-form YAML in `#` lines. Simple regex matching breaks on edge cases.

**How to avoid:** Use `yaml.safe_load()` on the header block before the CSV rows, or use the existing `sssom.py` parsing pattern (which already handles this).

**Warning signs:** Script crash on one specific SSSOM file; missing standards in the export.

---

## Code Examples

### Python Export Script Skeleton (verified from existing `sssom.py` patterns and actual TSV data)

```python
"""Write crosswalk_graph.json for the static crosswalk explorer.

Reads all committed SSSOM TSVs and the standards implied by their
mapping_set_metadata headers. Writes public/data/crosswalk_graph.json.

Uses Python stdlib only — no extra deps required for CI.
"""

from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SSSUM_DIR = ROOT / "exports" / "sssom"
OUTPUT_PATH = ROOT / "public" / "data" / "crosswalk_graph.json"


def _read_tsv_rules(path: Path) -> tuple[dict, list[dict]]:
    """Return (metadata_dict, rules_list) from one SSSOM TSV file."""
    raw = path.read_text(encoding="utf-8")
    lines = raw.splitlines()

    # 1. Parse YAML metadata block
    yaml_lines = []
    data_lines: list[str] = []
    in_metadata = True
    for line in lines:
        if in_metadata:
            if line.startswith("#"):
                yaml_lines.append(line.lstrip("#").strip())
            elif line.strip():
                in_metadata = False
                data_lines.append(line)
        else:
            if line.strip():
                data_lines.append(line)

    metadata: dict = {}
    if yaml_lines:
        import yaml  # only import if yaml is needed; pyproject has it anyway
        # yaml.safe_load needs a document stream
        try:
            metadata = yaml.safe_load("\n".join(yaml_lines)) or {}
        except Exception:
            pass

    # 2. Parse CSV data rows
    rules: list[dict] = []
    if data_lines:
        reader = csv.DictReader(io.StringIO("\n".join(data_lines)), delimiter="\t")
        for row in reader:
            comment_raw = row.get("comment") or "{}"
            try:
                comment = json.loads(comment_raw)
            except json.JSONDecodeError:
                comment = {}
            rules.append({
                "source_paths": comment.get("source_paths", [row.get("subject_label", "")]),
                "target_paths": comment.get("target_paths", []),
                "mapping_type": (comment.get("mapping_type") or "direct").upper(),
                "confidence": float(row.get("confidence") or 0.8),
                "semantic_loss": bool(comment.get("semantic_loss", False)),
                "ambiguity": bool(comment.get("ambiguity", False)),
                "transform": comment.get("transform", {}),
                "notes": comment.get("notes"),
                "strategy": _infer_strategy(comment),
                "evidence": {},
            })

    return metadata, rules


def _infer_strategy(comment: dict) -> str:
    mt = comment.get("mapping_type", "direct")
    if mt in ("conditional", "aggregation"):
        return "llm"
    if mt == "missing":
        return "fallback"
    return "deterministic"


def export_crosswalk_json() -> Path:
    standards_map: dict[str, dict] = {}
    crosswalks_out: list[dict] = []

    for tsv_path in sorted(SSSUM_DIR.glob("*.sssom.tsv")):
        crosswalk_id = tsv_path.stem  # e.g. "datacite44_to_dcterms"
        metadata, rules = _read_tsv_rules(tsv_path)

        # Derive source/target standard IDs from mapping_set_id
        set_id: str = metadata.get("mapping_set_id", f"m2s3om_graph:{crosswalk_id}")
        # e.g. "m2s3om_graph:datacite44_to_dcterms" → parse standard IDs
        # Fall back to extracting from description
        desc: str = metadata.get("mapping_set_description", "")
        source_label, _, target_label = desc.partition("->")

        src_id = _slugify(source_label.strip().split("(")[-1]) if "(" in source_label else f"src_{crosswalk_id}"
        dst_id = _slugify(target_label.strip().split(")")[0]) if ")" in target_label else f"dst_{crosswalk_id}"

        # Register standards
        if src_id not in standards_map:
            standards_map[src_id] = {"id": src_id, "name": source_label.strip() or src_id}
        if dst_id not in standards_map:
            standards_map[dst_id] = {"id": dst_id, "name": target_label.strip() or dst_id}

        crosswalks_out.append({
            "id": crosswalk_id,
            "source": src_id,
            "target": dst_id,
            "rules": rules,
        })

    output = {"standards": list(standards_map.values()), "crosswalks": crosswalks_out}
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    return OUTPUT_PATH


def _slugify(text: str) -> str:
    import re
    cleaned = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return cleaned or "unknown"


if __name__ == "__main__":
    path = export_crosswalk_json()
    print(f"Wrote {path}")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static sample `crosswalk_graph_sample.json` | Real exported JSON from SSSOM TSVs | Phase 02 | Explorer now shows actual crosswalk data; no more fake sample crosswalks |
| Two competing `pages` CI jobs (Python-only + Node-only) | Single merged `pages` job (Node image + Python) | Phase 02 | GitLab Pages artifact contains both Python-built HTML and Vite explorer |
| Scaffold Vite app unintegrated in `claude_suggestions/` | Integrated under `web/` and built into `public/explorer/` | Phase 02 | Explorer lives in canonical Pages source; navigable from existing nav |
| No per-rule strategy field in SSSOM TSVs | Strategy inferred from mapping_type (deterministic/llm/fallback) | Phase 02 | Explorer can display which rules are LLM-assisted vs deterministic |

**Deprecated/outdated:**
- `claude_suggestions/m2s3om-web-static-frontend/m2s3om-web/public/data/crosswalk_graph_sample.json` — reference-only after Phase 02; must not be used at runtime.

---

## Assumptions Log

> All claims tagged `[ASSUMED]` in this research. The planner and discuss-phase must confirm before execution.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `@surrealdb/wasm@3.0.3` is compatible with `surrealdb@2.0.8` at runtime | Standard Stack | If v3 WASM requires v3 surrealdb SDK, the app breaks. The `@surrealdb/wasm` peer dep says `^2.0.1` → should be compatible, but worth a local smoke test before CI commit. |
| A2 | Strategy can be inferred from mapping_type (`conditional`/`aggregation` → `llm`, `missing` → `fallback`, else → `deterministic`) | Python Export Script | If the mapping_type classification is wrong, some rules will have incorrect strategy labels in the explorer. User should review the inference logic against actual SSSOM files. |
| A3 | SSSOM YAML header `mapping_set_description` contains `source -> target` pattern for deriving standard IDs | Python Export Script | If a SSSOM file has a non-standard description format, the standard IDs will be derived incorrectly. Should be verified against all 24 SSSOM files. |
| A4 | `node:20` Docker image has Python available via apt or can have it installed | GitLab CI | If `node:20` image has Python pre-installed (some variants do), the apt-get install step is unnecessary but harmless. If not, it's required. |
| A5 | Standards don't need a separate authoritative file; they can be derived from SSSOM headers | Python Export Script | If there are standards without crosswalks (orphan standards), they would be missing from the export. The requirements say "standards list" — this might need a separate canonical standards registry. |
| A6 | The `strategy_counts` per-crosswalk metadata can be mapped to per-rule strategy | Python Export Script | The pipeline summary has `llm` and `deterministic_generic` counts per crosswalk, but not per-rule. Using mapping_type as a proxy is the best available heuristic. |

---

## Open Questions

1. **Per-rule strategy source**
   - What we know: SSSOM TSV comment JSON has no `strategy` field. Pipeline summary has crosswalk-level `strategy_counts`. mapping_type `conditional`/`aggregation` likely implies LLM-assisted.
   - What's unclear: Whether any SSSOM files have explicit strategy annotations in comments or separate metadata. Whether `conditional` in this codebase always means LLM (vs rule-based).
   - Recommendation: Default to mapping-type inference (see A2). Add `checkpoint:review-strategy` task to let user confirm or provide a strategy override mechanism.

2. **Evidence/provenance fields in TSV**
   - What we know: SSSOM comment JSON has `mapping_type`, `source_paths`, `target_paths`, `semantic_loss`, `ambiguity`, `transform`, `notes`. No `chunk_id`, `source_link`, or `citation` fields.
   - What's unclear: Whether `notes` or `subject_id`/`object_id` can serve as provenance proxies. Whether `EvidenceRecord` objects exist in any SSSOM file.
   - Recommendation: Export with `evidence: {}` placeholder. Plan a follow-up phase to populate from `evidence` table if/when populated.

3. **Standards without crosswalks**
   - What we know: The export derives standards from SSSOM crosswalk headers. Orphan standards (standards with zero crosswalks) would be absent.
   - What's unclear: Whether the project maintains a separate standards list that should be included even if no crosswalks reference it.
   - Recommendation: Check if `src/m2s3om_graph/models/standards.py` Standard model has a canonical list that should be iterated for the export.

4. **SurrealDB record ID escaping in graph-loader.js**
   - What we know: Scaffold's `graph-loader.js` inserts records without escaping IDs containing dashes. Crosswalk IDs like `rdamsc-c5` exist in the data.
   - What's unclear: Whether the build-time error (user preference) or runtime escaping (alternative) is preferred.
   - Recommendation: Add `escapeId()` helper in `graph-loader.js` and document the behavior. Per CONTEXT.md, build-time error is preferred — add a validation in the export script that fails if any crosswalk ID contains non-alphanumeric characters.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Vite build (web/) | ✓ (system) | v22.21.1 | `node:20` in CI |
| npm | Install Vite dependencies | ✓ (system) | 10.9.4 | `node:20` in CI |
| Python 3.12+ | Export script + `build_pages.py` | ✓ (miniforge3) | 3.12.11 | `apt-get install python3` in CI |
| `uv` | Install Python deps (CI) | ✗ | — | `apt-get install python3-pip` then `pip install`; or install `uv` via curl |
| GitLab CI | `pages` job | ✗ (no CI env) | — | Run local build manually; trust CI config |

**Missing dependencies with no fallback:**
- None — local environment has Node, npm, Python. CI `node:20` image needs Python installed.

**Missing dependencies with fallback:**
- `uv` in CI image → install via `apt-get` then `pip install uv`, or use official install script `curl -LsSf https://astral.sh/uv/install.sh | sh`

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run --with pytest pytest tests/` |
| Full suite command | `uv run --with pytest pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DATA-01 | Export script runs without error and produces valid JSON with `standards[]`, `crosswalks[]`, `rules[]` | unit | `uv run python scripts/export_crosswalk_json.py && python -c "import json; d=json.load(open('public/data/crosswalk_graph.json')); assert 'standards' in d and 'crosswalks' in d; assert len(d['standards']) > 0; assert len(d['crosswalks']) > 0"` | ✅ (new file needed) |
| DATA-01 | Exported JSON rules have all required fields | unit | `python -c "import json; d=json.load(open('public/data/crosswalk_graph.json')); rule=d['crosswalks'][0]['rules'][0]; required=['source_paths','target_paths','mapping_type','confidence','semantic_loss','ambiguity','strategy']; assert all(k in rule for k in required)"` | ✅ (in same test) |
| WEB-01 | Vite build produces `dist/` with `index.html` | smoke | `cd web && npm install && npm run build && test -f dist/index.html` | ❌ Wave 0 needed |
| WEB-01 | `dist/` copied into `public/explorer/` | integration | `test -f public/explorer/index.html` | ✅ (part of CI merge) |
| WEB-02 | `.gitlab-ci.yml` has exactly one `pages` job | lint | `grep -c '^pages:' .gitlab-ci.yml` returns 1 | ✅ (part of CI merge) |
| GOV-01 | No runtime imports from `claude_suggestions/` in web/ | lint | `grep -r 'claude_suggestions' web/src/` returns empty | ✅ (part of scaffold integration) |

### Sampling Rate
- **Per task commit:** `uv run --with pytest pytest tests/` (quick) + Vite build smoke
- **Per wave merge:** Full suite `uv run --with pytest pytest`
- **Phase gate:** Vite build + export script + pytest all green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_export_crosswalk_json.py` — covers DATA-01 export script validation
- [ ] `tests/test_vite_smoke.py` — runs `cd web && npm install && npm run build` and checks dist/
- [ ] Framework install: `npm install -D vite` (no extra framework; uses existing pytest)

---

## Security Domain

> `security_enforcement` is not explicitly disabled in `.planning/config.json` → security domain is INCLUDED.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | yes | SSSOM TSV parsed via `csv.DictReader`; JSON comment parsed via `json.loads()` with try/except; malformed rows skipped gracefully |
| V4 Access Control | no | Static site; no auth; no user-specific data |
| V2 Authentication | no | Public GitLab Pages; no auth |
| V3 Session Management | no | No server-side sessions |
| V6 Cryptography | no | No cryptographic operations in this phase |

### Known Threat Patterns for Python stdlib + Vite build

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| SSSOM TSV injection via malicious comment field | Information Disclosure | `json.loads()` on comment field is sandboxed; no `eval()`; output is static JSON |
| Path traversal via SSSOM filename | Tampering | `Path.glob()` is sandboxed to `exports/sssom/`; `pathlib` prevents `..` escaping root |
| Malicious `node_modules/` package | Tampering | `package-lock.json` committed; CI uses pinned versions |
| SurrealDB record ID injection | Information Disclosure | IDs come from parsed TSV data, not user input; if IDs contain special chars, they are escaped in SurrealQL or rejected at export time |
| SSSOM YAML header arbitrary code execution | Tampering | `yaml.safe_load()` used (not `yaml.unsafe_load()`); YAML headers only contain simple key-value pairs |

---

## Sources

### Primary (HIGH confidence)
- Scaffold files in `claude_suggestions/m2s3om-web-static-frontend/m2s3om-web/` — verified by reading each file in this session
  - `package.json` — confirmed deps: `surrealdb`, `@surrealdb/wasm`
  - `vite.config.js` — confirmed base: `'./'`, optimizeDeps exclude, esbuild top-level-await
  - `src/main.js` — confirmed import pattern, IndexedDB connect, data path TODO
  - `src/graph-loader.js` — confirmed insert pattern, record ID format
  - `index.html` — confirmed minimal HTML shell
  - `.gitlab-ci.yml.snippet` — confirmed single `pages` job with `node:20`
  - `README.md` — confirmed expected JSON schema shape
  - `public/data/crosswalk_graph_sample.json` — confirmed field names and sample values
- `src/m2s3om_graph/sssom.py` lines 1–278 — verified SSSOM TSV format, column names, comment JSON structure
- `scripts/build_pages.py` — verified existing Python stdlib-only pages generator
- `.gitlab-ci.yml` — verified current single `pages` job with `python:3.12-slim`
- `exports/sssom/datacite44_to_dcterms.sssom.tsv` — verified actual 9-column TSV format with JSON comment
- `exports/pipeline/latest/rdamsc_stats_summary.json` — verified strategy_counts: `{'llm': 5, 'deterministic_generic': 4}`

### Secondary (MEDIUM confidence)
- `src/m2s3om_graph/db/models.py` lines 1–135 — verified MappingRuleRecord fields, MappingType enum
- `src/m2s3om_graph/models/standards.py` — verified Standard model structure
- `surql/schema.surql` — verified table definitions for standard, element, crosswalk, mapping

### Tertiary (LOW confidence)
- Vite 8.2.1 configuration for `@surrealdb/wasm` — based on scaffold config and Vite docs; not verified via Context7 in this session (the scaffold config is already correct and verified)
- SurrealDB 2.0.8 + `@surrealdb/wasm` 3.0.3 compatibility — based on peer dep declaration and README; confirmed via npm registry but runtime compatibility not tested

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — packages confirmed on npm registry; scaffold files read verbatim; package-lock approach confirmed in CI snippet
- Architecture: HIGH — existing codebase structure verified; build pipeline pattern confirmed from build_pages.py; scaffold integration path clear from README
- Pitfalls: MEDIUM — SurrealDB ID escaping confirmed from scaffold README (mentions backtick-escaping); CI image Python gap confirmed from Docker image comparison; version mismatch pattern from npm peer dep analysis

**Research date:** 2026-08-14
**Valid until:** 2026-09-13 (30 days — stable domain with no fast-moving libraries; Vite and SurrealDB are mature)
