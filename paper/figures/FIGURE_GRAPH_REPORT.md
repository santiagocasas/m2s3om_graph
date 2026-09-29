# Graph Figure — Diagnosis, Topics, and Figure Report

**Scope:** `scripts/standard_topics.json`, `scripts/make_graph_figure.py`, `paper/figures/graph_topics.{pdf,png}`, this file.
**Constraints honored:** `exports/` and `paper/main.tex` were never modified — confirmed via `git status --short` before and after this work; only files under `scripts/` and `paper/figures/` were created.

---

## Part A — Diagnosis (nothing changed)

### A.1 — Is the `rdamsc_c38` self-loop an RDAMSC-record artifact or ours?

**Ours — a defect in our entity-resolution code**, though RDAMSC's own record is genuinely ambiguous and made the bug possible.

Live query:
```python
from m2s3om_graph.rdamsc.api import RDAMSCClient
RDAMSCClient().get_mapping_detail("c38")["relatedEntities"]
```
returns, in this exact order:
```
[msc:m11 (DataCite)  role=input scheme,
 msc:m124(DCAT-AP)   role=input scheme,
 msc:g145            role=maintainer,
 msc:m11 (DataCite)  role=output scheme,
 msc:m124(DCAT-AP)   role=output scheme]
```
RDAMSC tags **both** DataCite and DCAT-AP as both input **and** output scheme — an upstream data-quality issue in the RDAMSC record itself.

Our code, `_source_target_entities()` in `src/m2s3om_graph/rdamsc/ingest.py:140-159`, resolves source/target independently and greedily:
```python
if role == "input scheme" and source_entity is None: source_entity = entity
if role == "output scheme" and target_entity is None: target_entity = entity
```
It takes the **first** match per role, not a paired input/output. Since `m11`'s "output scheme" entry precedes `m124`'s "output scheme" entry in the list, this picks `source=m11, target=m11` → the self-loop. The domain-correct pairing would be `source=m11 (DataCite) → target=m124 (DCAT-AP)`.

**Verdict:** the self-loop is a defect in `_source_target_entities()`'s first-match-per-role selection, not an unavoidable consequence of the RDAMSC record.

### A.2 — Where does the edge "relationship" (LLM/deterministic) actually come from?

**Correction:** the user-named `scripts/export_crosswalk_json.py` is **not** the source of the canonical `exports/graph/crosswalk_graph.json` used throughout this audit. That script only writes a separate web-app export (`web/public/data/crosswalk_graph.json`, `web/data/crosswalk_graph.json`) with its own per-rule `infer_strategy()` (lines 75-81) driven by `mapping_type` (conditional/aggregation→llm, missing→fallback, else→deterministic) — not by actual extractor backend.

**The actual source of `exports/graph/crosswalk_graph.json` is `scripts/export_graph.py`**, function `determine_extraction_strategy(crosswalk_id, metadata)` (lines 78-96):
```python
if crosswalk_id in ["rdamsc_c36", "rdamsc_c38"]:
    return "deterministic"   # hardcoded allowlist, comment cites an external narrative doc
elif "llm" in str(metadata).lower():
    return "llm"             # checks for literal substring "llm" in the SSSOM header dict — almost never true
elif crosswalk_id.startswith("rdamsc_"):
    return "llm"             # blanket default
else:
    return "unknown"
```
In practice: **exactly 2 crosswalks (c36, c38) are ever labeled deterministic**; every other `rdamsc_*` edge is unconditionally labeled `llm` regardless of true extraction method; the curated `datacite44_to_dcterms` edge gets `unknown`.

**Comparison against `exports/pipeline/strategies.csv` (this audit's own, evidence-based classification), all 25 rdamsc crosswalks with a graph edge — 6 mismatches:**

| Crosswalk | `export_graph.py` says | `strategies.csv` says | Match? |
|---|---|---|---|
| c1 | llm (default) | deterministic | ❌ |
| c5 | llm (default) | curated / structured PDF path | ❌ |
| c11 | llm (default) | deterministic | ❌ |
| c18 | llm (default) | deterministic | ❌ |
| c28 | llm (default) | deterministic | ❌ |
| c34 | llm (default) | deterministic | ❌ |
| c3, c13, c14, c19, c20, c21, c22, c23, c24, c26, c27, c29, c30, c32, c33, c35, c36, c37, c38 (19) | — | — | ✅ (agree, either genuinely LLM or c36/c38's hardcode happens to be right) |

**This figure therefore does not use `export_graph.py`'s strategy field** — it uses `exports/pipeline/strategies.csv` instead (see Part C).

### A.3 — Duplicate node pairs and their attached edges

`exports/graph/crosswalk_graph.json` (24 nodes, 26 edges, HEAD) contains two node pairs referring to the same real-world standard:

| Node id | Label | Attached edges |
|---|---|---|
| `rdamsc_m11` | DataCite Metadata Schema | `rdamsc_c38` (self-loop, source=target=`rdamsc_m11`, deterministic, 160 rows); `rdamsc_c5` (source, →`rdamsc_m15`, curated, 24 rows) |
| `datacite_4_4` | DataCite | `datacite44_to_dcterms` (source, →`dublin_core_terms`, curated, 110 rows) |
| `rdamsc_m15` | Dublin Core | 8 edges: c11(source→rdamsc_m88, 60), c21(rdamsc_m88→target, 83), c24(rdamsc_m39→target, 13), c26(source→rdamsc_m97, 36), c27(rdamsc_m97→target, 26), c32(source→rdamsc_m98, 8), c35(source→rdamsc_m114, 41), c5(rdamsc_m11→target, 24) |
| `dublin_core_terms` | Dublin Core Terms | `datacite44_to_dcterms` (target only) |

**Effect:** the curated `datacite44_to_dcterms` edge is structurally disconnected from all 9 `rdamsc_*` edges touching DataCite/Dublin Core, even though they describe overlapping standard pairs.

**Proposed smallest fix (not applied — diagnose-only):** redirect the curated edge's `source`/`target` to point at `rdamsc_m11`/`rdamsc_m15` instead of the separate `datacite_4_4`/`dublin_core_terms` ids (keep `rdamsc_m11`/`rdamsc_m15` as canonical since they carry the real rdamsc-pipeline edges). Likely a one-line change in `export_graph.py`'s node-id assignment for the curated file (its curie_map resolves to different ids than the rdamsc files' curie_map). **This does not drop `c5`** — `c5`'s own edge (`rdamsc_m11`→`rdamsc_m15`) is untouched; only the duplicate node pair is removed, so the curated edge and `c5`'s edge would then correctly share endpoints.

---

## Part B — Topics (`scripts/standard_topics.json`)

**⚠️ Status: DRAFT, needs review. Do not use for the paper until approved.**

No literal topic table was present in the request this file responds to (the message referenced "the draft table in the notes below" but no table followed). As a substitute starting point, this file inherits the `type` field already present on 20 of the 24 current node ids in the older `data/crosswalks.human.json` graph, which happens to use exactly the 7 requested topic names.

- **20/24 node ids**: inherited directly from `data/crosswalks.human.json`'s existing `type` field (source noted as that file).
- **`datacite_4_4`** → FAIR data commons (inherited from its duplicate-pair partner `rdamsc_m11`, cross-referenced to the A.3 finding above).
- **`dublin_core_terms`** → FAIR data commons (inherited from `rdamsc_m15`, same cross-reference).
- **`rdamsc_m21` (ISA-Tab) and `rdamsc_m87` (MAGE-TAB)** — added to the graph later via crosswalk c19, absent from the older 20-node file. Both assigned **Health** as a best-effort grouping (life-sciences investigation/microarray formats, alongside the other Health-bucketed biodiversity/life-science standards), each explicitly marked `"DRAFT best-effort — NEEDS REVIEW"` in the `source` field.
- SPASE's topic spelling normalized from the source file's "Aeronautics Space Transport" to the requested "Aeronautics/Space/Transport".

File structure: `_status`, `_note` (explains the substitution above), `_topics` (list of the 7 canonical names), `assignments: {node_id: {label, topic, source}}`.

---

## Part C — Figure

**Script:** `scripts/make_graph_figure.py` (new, ~230 lines). **Command:** `uv run python scripts/make_graph_figure.py`.
**Outputs:** `paper/figures/graph_topics.pdf` (vector, `pdf.fonttype`=42), `paper/figures/graph_topics.png` (300 dpi). Figure size fixed at **exactly 17cm × 9cm** — verified via `pdfinfo`: `481.89 × 255.118 pt` = 6.693in × 3.543in = 17.0cm × 9.0cm.

**Data sources, all read-only, none from `export_graph.py`'s buggy strategy field:**
- **Layout:** fixed x/y coordinates already present on each node in `exports/graph/crosswalk_graph.json` (not re-laid-out).
- **Node color:** topic, from `scripts/standard_topics.json` (Part B), 7-color Okabe-Ito-derived palette.
- **Edge line style:** `exports/pipeline/strategies.csv` (Part A.2's corrected classification), not `export_graph.py`'s field — `deterministic*` → dashed, `llm*`/`llm_relaxed` → solid, `curated*` → dotted.
- **Edge rule-count labels:** raw row counts from `exports/sssom/*.sssom.tsv` (header/`#` lines excluded), **not** the graph's `rule_count` field, which the freeze audit (`AUDIT_REPORT_2026-09-29_freeze.md`, item 5) found is systematically inflated by exactly +1 versus the true file row count.
- **Edges:** dark gray (`#3B3B3B`) throughout, slightly curved.

**Run result:** 24 nodes, 26 edges, zero warnings (every node had a topic, every edge had a resolvable row count). Edge style counts: `deterministic=7` (c1, c11, c18, c28, c34, c36, c38), `llm=17`, `curated=2` (c5, datacite44_to_dcterms).

**Self-loop and duplicate nodes — kept exactly as exported, per instruction, and marked rather than fixed:**
- The `rdamsc_c38` self-loop (A.1) is drawn as a small loop arc above the `rdamsc_m11` node, annotated with its row count (160).
- The two duplicate node pairs (A.3: `datacite_4_4`/`rdamsc_m11`, `dublin_core_terms`/`rdamsc_m15`) each carry a small red asterisk marker near the node, with a legend entry explaining they are known-duplicate, unmerged nodes. They are **not** visually connected or merged in this figure — Part A's proposed fix was intentionally **not** applied here.

**Legend:** two-part — topic → color (top-left), edge style/self-loop/duplicate-marker meanings (bottom-left).

---

## Files touched by this task

- `scripts/standard_topics.json` (new)
- `scripts/make_graph_figure.py` (new)
- `paper/figures/graph_topics.pdf`, `paper/figures/graph_topics.png` (new)
- `paper/figures/FIGURE_GRAPH_REPORT.md` (this file, new)

`exports/` and `paper/main.tex` were not modified at any point in Parts A, B, or C.

---

## Layout fix (2026-09-29, follow-up — only `scripts/make_graph_figure.py` touched)

**What changed:** replaced the graph's own circular x/y layout with a per-connected-component `networkx.kamada_kawai_layout`, packed into a left panel (largest component, ~55% width) plus a 2x2 grid for the other four; switched all 24 node ids to the exact fixed `SHORT_LABELS` dict; dropped rule-count numbers from all non-self-loop edges (kept only on the 160-row self-loop); node size now scales with degree (60–220 pt²) and edge width with sqrt(row count) (0.6–3pt); only genuinely parallel/opposite-direction edge pairs (MARC↔Dublin Core, MODS↔Dublin Core, MARC↔MODS, ABCD↔Darwin Core) are drawn curved (`arc3,rad=0.2`), everything else straight; labels use a bounding-box-overlap-aware above/below placement (not just point distance) plus a white-halo path effect, after one follow-up fix so the self-loop circle also counts as a label obstacle. Topic colors, the legend, all four data sources, the duplicate-node asterisks, and the output filenames are all unchanged from the original Part C script.
**Final figure size:** 17.0cm × 11.0cm (confirmed via `pdfinfo`: 481.89×311.811pt), bumped from 9cm as permitted because the 11-node left component needed the extra height.
**Command:** `uv run --with networkx --with scipy python scripts/make_graph_figure.py` (scipy is an indirect dependency of `kamada_kawai_layout`, not listed in the original run instruction but required by networkx itself).
**Components found:** 5, as expected — sizes 11 (Dublin Core/MARC/MODS/CIDOC CRM hub, left panel), 5 (ABCD/Darwin Core/OECD/HISPID/EURISCO), 4 (EML/ISO 19115/DDI/NetCDF ACDD), 2 (ISA-Tab/MAGE-TAB), 2 (DataCite/DC Terms, the curated pair).
**Hardest label to place:** the duplicate-node asterisk on `rdamsc_m15` (Dublin Core) sits close to the "Dublin Core" label itself — the hub node has 8 incident edges converging from most directions, leaving little clear space for the marker; it is legible but not as cleanly separated as the other three duplicate markers. The self-loop's "DataCite (RDAMSC)" / "160" cluster was also tight (fixed by treating the loop as a label obstacle) but is now clear.
