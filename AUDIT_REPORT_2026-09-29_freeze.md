# RDAMSC Pipeline Freeze Audit — 2026-09-29

**Repo:** `/home/casas/AI/m2s3om_graph`
**Context:** `make pipeline-run-freeze` was run earlier today (2026-09-29) without `--force`. It did **not** re-extract anything: 25/37 crosswalks were backfilled from existing SSSOM files (`result.step="kg_backfill"`), 12/37 were freshly retried and all failed at the artifact-fetch stage, `exports/pipeline/latest/` now shows 14 fresh artifact-check records, and no crosswalk in this run's status file carries a `strategy` value.
**Constraints honored throughout:** no `--force` used, `exports/sssom/*.sssom.tsv` never modified (verified repeatedly), nothing committed, `paper/` never touched.

---

## 1. `git status` / `git diff --stat -- exports/` — did the freeze change anything tracked?

**Commands:**
```bash
git status --short
git diff --stat -- exports/
git diff --stat -- exports/sssom/
git ls-files exports/pipeline/latest
git diff -- exports/pipeline/latest/rdamsc_artifacts.csv
wc -l exports/pipeline/latest/rdamsc_artifacts.csv
git show HEAD:exports/pipeline/latest/rdamsc_artifacts.csv | wc -l
```

**Result:** `git status --short` shows changes **only** under `paper/figures/` and `scripts/make_paper_figures.py` (pre-existing, unrelated to today's freeze run — figure-generation work from earlier in this session). **Nothing under `exports/` appears at all.** `git diff --stat -- exports/` and `git diff --stat -- exports/sssom/` are both completely empty.

All 7 tracked files under `exports/pipeline/latest/` (`pipeline.log`, 5 `plots/*.png`, `rdamsc_artifacts.csv`, `rdamsc_crosswalks.csv`, `rdamsc_pipeline_status.json`, `rdamsc_stats_summary.json`, `run_metadata.json`) show `mtime` of today (15:05) on disk — **the freeze run did execute and rewrite these files** — but every one is byte-identical to what's already committed at HEAD (`rdamsc_artifacts.csv`: 25 lines before and after, confirmed via `wc -l` vs `git show HEAD:... | wc -l`).

**No `*.sssom.tsv` file changed content.** 26 files present, zero diff.

**The only real change from today's run lives in the gitignored `.local/rdamsc_pipeline_status.json`** (fresh, mtime 15:00):
- 37 total entries. `Counter(status) = {ready: 25, failed_unreachable: 12}` — no `failed_parse` this run.
- `Counter(result.step) = {kg_backfill: 25, None: 12}` — all 25 "ready" entries were backfilled from existing SSSOM files, not re-extracted. The 12 `failed_unreachable` entries are the ones actually retried; they never reach a KG/backfill step because they fail earlier, at artifact-fetch.
- **0/37 entries carry a non-empty `result.strategy` field** — confirms the "no strategy data" claim exactly.
- **14 `artifact_checks` records total, across 12 crosswalks** — confirms the "14 artifact checks" claim exactly. Per-crosswalk breakdown: `c15`×2, `c17`×2, and one each for `c2, c4, c6, c7, c8, c9, c10, c12, c16, c31`.
- Notable: `rdamsc_c2` is `failed_unreachable` in this fresh run. In older snapshots (March/June) `c2` was marked "ready" with no SSSOM file on disk — an old inconsistency. Today's live retry resolves that ambiguity: `c2` is genuinely unreachable.

**Verdict: item 1 confirmed exactly as described by the user.** No tracked file, and specifically no `*.sssom.tsv`, changed. The freeze run only refreshed a gitignored local cache with content identical to HEAD, plus updated the gitignored status JSON with today's retry outcomes for the 12 unreachable crosswalks.

---

## 2. Full live artifact-URL check — `scripts/check_artifact_urls.py`

**New script:** `scripts/check_artifact_urls.py` (untracked, not committed). Since no persisted RDAMSC catalog JSON exists anywhere in the repo (`data/` has only `crosswalks.human.json`; `.local/` has no raw catalog dump), "synced RDAMSC data" is obtained by calling the **live** RDAMSC API (`RDAMSCClient.get_mapping_detail(msc_id)`, `src/m2s3om_graph/rdamsc/api.py`) for each of the 37 known `msc_id` values (source: `.local/rdamsc_pipeline_status.json`), then reading `locations[].url` from each detail payload — this is exactly the input `_fetch_artifacts()` (`src/m2s3om_graph/rdamsc/ingest.py:637`) consumes internally, so URL coverage matches the pipeline.

For the HTTP check itself, the script imports `DEFAULT_HEADERS` and `_candidate_urls` directly from `m2s3om_graph.rdamsc.artifacts` — guaranteeing byte-identical headers and the same GitHub-raw / http→https fallback chain the pipeline uses — but performs its own raw `requests.get` (rather than calling `fetch_artifact_text`, which only returns converted markdown with no size/hash/content-type of the raw response). This is documented in the script's docstring. Each URL is retried up to 3 attempts total, 10s apart, on failure; failures are classified into `dns_failure`, `connection_reset`, `connection_error`, `http_403`, `http_404`, `other_http_error`, `timeout`, or `other_exception`.

**Command:**
```bash
uv run python scripts/check_artifact_urls.py \
  --output-csv exports/pipeline/latest/rdamsc_artifacts_full.csv \
  --output-summary exports/pipeline/latest/rdamsc_artifacts_full_summary.json
```
Ran live, completed in 13m5s, full per-URL progress logged (no silent hangs). Output verified: `wc -l rdamsc_artifacts_full.csv` = 50 lines (49 rows + header, matches `total_urls`); `git status --short` shows both output files as new/untracked; `exports/sssom/` unaffected.

**Summary (generated_at 2026-09-29T13:30:19Z):**

| | |
|---|---|
| Total URLs | **49** |
| Fetched | **22** |
| Failed | **27** |

**Failed by host:**

| Host | Failures |
|---|---|
| www.loc.gov | 10 |
| service.ncddc.noaa.gov | 5 |
| gcmd.nasa.gov | 3 |
| www.ands.org.au | 3 |
| schema.datacite.org | 3 |
| www.w3.org | 1 |
| wiki.esipfed.org | 1 |
| www.ddialliance.org | 1 |

**Failed by reason:** `http_403`=14, `connection_reset`=5, `http_404`=5, `connection_error`=3.

**Crosswalks — all artifacts fetched (16):** c1, c3, c5, c13, c14, c18, c19, c20, c23, c24, c33, c34, c35, c36, c37, c38.
**Crosswalks — some fetched (1):** c22 (one URL 404'd, the other succeeded via GitHub raw fallback).
**Crosswalks — none fetched (20):** c2, c4, c6, c7, c8, c9, c10, c11, c12, c15, c16, c17, c21, c26, c27, c28, c29, c30, c31, c32.

**Key per-crosswalk detail:**
- `c4`, `c6`, `c7` each reference the **identical** `schema.datacite.org` kernel-2.2 PDF, which now 404s for all three.
- `c5`'s DataCite 4.4 → Dublin Core PDF (the same PDF underlying the curated benchmark crosswalk) **still fetches successfully** — the curated source is live and unchanged.
- `c15`, `c17`, `c2` (all NOAA NCDDC XSLT/XLS crosswalks) — `connection_reset` on every URL.
- `c11, c21, c26, c27, c28, c29` (all MODS/MARC/Dublin-Core crosswalks hosted at loc.gov) — uniform `http_403` on every URL, 6 attempts each (both the http and https candidate exhausted their 3 retries).
- `c30, c31, c32` — `www.ands.org.au` zip URLs, `http_403`.
- `c12` — `www.w3.org/TR/prov-dc/`, `http_403`.

**Finding: live reachability has shifted since the paper's March 2026 source snapshot (`5dc8e248`), independent of any pipeline bug.** At `5dc8e248`, total URLs were 45 with `loc.gov` not a major failure source; today `loc.gov` alone accounts for 10/27 failures (all `http_403`), consistent with LOC having added bot-blocking sometime after March. NASA GCMD (3) and schema.datacite.org (3) failure counts match the paper's historical figures exactly; NOAA NCDDC is 5 today vs. the paper's 4. **Today's true total is 49 URLs, not 45 (paper) and not 24 (HEAD's stale committed `rdamsc_artifacts.csv`, which was never refreshed to a full sweep after early pipeline runs).**

---

## 3. Per-SSSOM-file provenance (26 files)

**`generation_manifest.json` has no per-file strategy field anywhere** — only `{file, sha256, size_bytes, mtime_utc}` per entry, plus an aggregate `pipeline_summary`. So "does the manifest record a strategy" is **NO for every file, uniformly**.

**`mapping_justification` is not a useful provenance signal**: every rdamsc file uses `semapv:ManualMappingCuration` (alone or with `semapv:CompositeMatching`) regardless of whether the rows were actually machine-extracted — this SSSOM field is effectively mislabeled/boilerplate and should not be cited as evidence of hand-curation.

**The reliable signal is the embedded `comment` JSON's `.notes` field**, which differs by extractor backend: `"Deterministic ..."` boilerplate for the deterministic extractor, `"Relaxed LLM extraction"` for the LLM fallback backend, or long descriptive per-field reasoning for the main LLM JSON backend. A third pattern, `notes: null` with fully structured fields and no free text, appears only in `datacite44_to_dcterms.sssom.tsv` and (partially) `rdamsc_c5.sssom.tsv` — a distinct **curated/structured PDF-ingestion path**, not the rdamsc web-artifact pipeline at all.

**Git-add provenance** (`git log --follow --diff-filter=A`) clusters all 26 files into 5 commits:

| Commit | Date | Message | Files added |
|---|---|---|---|
| `c9575e4` | 2026-03-02 | "first publishing commit of working app" | datacite44_to_dcterms, c11, c5 |
| `f4e040e` | 2026-03-03 | "new pipeline run, generated sssom files, created provenance and manifest and stats scripts for pipeline" | c13, c14, c20, c21, c22, c24, c26, c27, c30, c32, c33, c35, c36, c37 |
| `5dc8e24` | 2026-03-05 | (freeze commit, used as historical baseline elsewhere in this audit) | c38 |
| `732c25d` | 2026-05-14 | **"plans"** — bundles 4 unrelated `.planning/*.md` docs with 6 SSSOM files; `git show --stat` confirms no `exports/pipeline/latest` or `.local` touched, i.e. **not** a genuine `make pipeline-run-freeze` invocation | c1, c18, c23, c28, c3, c34 |
| `a592f22` | 2026-08-17 | **"feat: add deployment templates and crosswalk fixtures"** — bundles Docker/deployment scaffolding with 2 SSSOM files; the word "fixtures" is itself a red flag | c19, c29 |

**Full 26-file table** (row count | git-add commit | extraction-method fingerprint from `comment.notes`):

| File | Rows | Added by | Fingerprint |
|---|---|---|---|
| datacite44_to_dcterms | 110 | c9575e4 | 99 curated (notes:null) + 11 LLM_RICH |
| c1 | 15 | 732c25d | 15 deterministic ("markdown-table") |
| c3 | 1 | 732c25d | 1 LLM_RELAXED |
| c5 | 24 | c9575e4 | 20 curated (notes:null) + 4 LLM_RICH |
| c11 | 60 | c9575e4 | 60 deterministic ("LOC DC→MARC crosswalk") |
| c13 | 37 | f4e040e | 37 LLM_RICH |
| c14 | 33 | f4e040e | 33 LLM_RICH |
| c18 | 13 | 732c25d | 13 deterministic ("markdown-table") |
| c19 | 2 | a592f22 | 2 LLM_RELAXED |
| c20 | 40 | f4e040e | 40 LLM_RICH |
| c21 | 83 | f4e040e | 83 LLM_RICH |
| c22 | 47 | f4e040e | 47 LLM_RICH |
| c23 | 23 | 732c25d | 23 LLM_RICH |
| c24 | 13 | f4e040e | 13 LLM_RICH |
| c26 | 36 | f4e040e | 36 LLM_RICH |
| c27 | 26 | f4e040e | 26 LLM_RICH |
| c28 | 92 | 732c25d | 76 deterministic (assignment) + 16 deterministic (markdown-table) |
| c29 | 77 | a592f22 | 77 LLM_RICH |
| c30 | 15 | f4e040e | 15 LLM_RICH |
| c32 | 8 | f4e040e | 8 LLM_RELAXED |
| c33 | 1 | f4e040e | 1 LLM_RELAXED |
| c34 | 56 | 732c25d | 56 deterministic ("markdown-table"; many `subject_label` values are literally the string `"NaN"` — a real extractor defect) |
| c35 | 41 | f4e040e | 41 LLM_RICH |
| c36 | 10 | f4e040e | 10 deterministic ("assignment-pattern") |
| c37 | 49 | f4e040e | 49 LLM_RICH |
| c38 | 160 | 5dc8e24 | 160 deterministic ("markdown-table") |

**Priority-list verdicts (c1, c2, c3, c18, c19, c23, c28, c29, c34):**

- **c2**: no SSSOM file exists at any commit examined, and the live check (item 2) confirms it is genuinely unreachable today (`connection_reset`). No hand-editing question applies — there is nothing to evaluate.
- **c1, c18, c28, c34**: deterministic-extractor content, added via the `732c25d` "plans" commit. Content fingerprint (structured JSON matching the deterministic extractor's exact field set, plus a genuine extractor defect — literal `"NaN"` strings in c34) is strong evidence these are **machine-extracted, not hand-authored**. However, `5dc8e248`'s own `rdamsc_crosswalks.csv` (March) shows these same 4 crosswalks as `failed_parse`/`strategy=llm` at that time — meaning **a later, successful deterministic re-extraction occurred between March and mid-May**, superseding an earlier failed LLM attempt, and the result was checked into git via a casual commit bundled with unrelated planning docs rather than a dedicated pipeline-run commit.
- **c3, c19, c23, c29**: LLM-extracted content (c3/c19 via the "relaxed" fallback backend, tiny 1–2 row outputs typical of that path; c23/c29 via the rich JSON backend with detailed, domain-specific reasoning e.g. MARC-field-specific text for c29, OECD-domain text for c23). Same pattern: these were `failed_parse` at `5dc8e248` (March) and succeeded on a later LLM retry, added via `732c25d` (c3, c23) or `a592f22` (c29).

**Explicit statement of uncertainty:** confidence is **high** that all 9 priority files' rule content is genuinely machine-extracted (the content fingerprint matches the pipeline's exact JSON schema — `mapping_type`, `source_paths`, `target_paths`, `transform`, `semantic_loss`, `ambiguity`, `notes` — with plausible, non-generic, domain-specific reasoning that would be unusual to fabricate by hand). There is **no direct proof of the exact run or date** that produced them, since the commits that added them bundle unrelated files (planning docs, deployment scaffolding) and no pipeline run log from that period survives. Nothing found suggests hand-authored/fabricated rules.

---

## 4. Extraction strategy recovered from git history — `exports/pipeline/strategies.csv`

**New file:** `exports/pipeline/strategies.csv` (37 rows + header, untracked). Built by cross-referencing `rdamsc_crosswalks.csv` at three snapshots (`5dc8e248` March, `a1e6f99` June, HEAD) against item 3's content-based classification.

**Strategy bookkeeping degraded over time**: at `5dc8e248` and `a1e6f99`, nearly every processed row carried an explicit `strategy` value (mostly `llm`, with c36/c38 = `deterministic_generic`). By HEAD, only 6 rows retain a value (c1, c18, c28, c34 = `deterministic_generic`; c3, c19, c23 = `llm`) plus one stray leftover (c31 = `llm` despite having no file at all — a bookkeeping artifact, not real).

**Final classification, all 37 crosswalks:**

- **Deterministic (7):** c1, c11, c18, c28, c34, c36, c38
- **Curated/structured PDF path (1, distinct from the rdamsc pipeline):** c5
- **LLM, rich backend (13):** c13, c14, c20, c21, c22, c23, c24, c26, c27, c29, c30, c35, c37
- **LLM, relaxed-fallback backend (4):** c3, c19, c32, c33
- **Gaps — no strategy ever succeeded (12):** c2, c4, c6, c7, c8, c9, c10, c12, c15, c16, c17, c31 — all `failed_unreachable` both historically and in today's live check (item 2); no extraction was ever attempted successfully because the artifact was never fetched.

This reconciles to **7 deterministic + 17 LLM (13 rich + 4 relaxed) + 1 curated + 12 unreachable = 37**, and to the 26 files on disk (7 deterministic + 17 LLM + 1 curated + 1 curated-adjacent c5... — note c5 is counted once, under "curated," giving 25 rdamsc-pipeline-attributable files + 1 curated-only `datacite44_to_dcterms` = 26 total files, matching the file count exactly).

---

## 5. Source/target standards and row counts — c5, c12, c35, c36, c38

| Crosswalk | Source → Target | File rows | Graph edge `rule_count` |
|---|---|---|---|
| c5 | DataCite Metadata Schema → Dublin Core | 24 | 25 |
| c12 | Dublin Core → PROV *(resolved via live RDAMSC API; no graph edge, no SSSOM file exists)* | **0 — no file** | — |
| c35 | Dublin Core → CIDOC CRM | 41 | 42 |
| c36 | EAD → CIDOC CRM | 10 | 11 |
| c38 | DataCite Metadata Schema → DataCite Metadata Schema *(self-loop; conceptually CiteDCAT-AP, but DCAT-AP has no node in the graph — see item 6)* | 160 | 161 |

`c12`'s source/target pair (Dublin Core → PROV) was resolved via a live `RDAMSCClient.get_mapping_detail()` call (`relatedEntities`: input scheme `msc:m15`=Dublin Core, output scheme `msc:m33`=PROV) since no SSSOM file or graph edge exists for it. Its one artifact URL (`https://www.w3.org/TR/prov-dc/`) returned `http_403` in today's live check.

**Systematic off-by-one confirmed**: every checked graph edge's `rule_count` equals its file's row count **plus exactly 1** (c5: 24→25, c35: 41→42, c36: 10→11, c38: 160→161) — a consistent bug in the graph-build script, most likely counting a header-derived pseudo-row. This should be fixed before citing `rule_count` values from `exports/graph/crosswalk_graph.json` as exact row counts.

---

## 6. Transitive paths in `exports/graph/crosswalk_graph.json` (A→B→C with no direct A→C edge)

Graph at HEAD (`f8de73b7`): 24 nodes, 26 edges. **17 two-hop paths found with no direct A→C edge**, sorted by total rule count (`rule_count`, the +1-inflated graph value):

| # | Path | Hop 1 (crosswalk, rules) | Hop 2 (crosswalk, rules) | Total |
|---|---|---|---|---|
| 1 | MODS → MARC → CIDOC CRM | c29 (78) | c37 (50) | 128 |
| 2 | MARC → Dublin Core → RIF-CS | c21 (84) | c32 (9) | 93 |
| 3 | NetCDF ACDD → ISO 19115 → DDI | c22 (48) | c20 (41) | 89 |
| 4 | **DataCite Metadata Schema → Dublin Core → MARC** | c5 (25) | c11 (61) | 86 |
| 5 | EML → ISO 19115 → DDI | c13 (38) | c20 (41) | 79 |
| 6 | SPASE → Dublin Core → MARC | c24 (14) | c11 (61) | 75 |
| 7 | MODS → Dublin Core → CIDOC CRM | c27 (27) | c35 (42) | 69 |
| 8 | **DataCite Metadata Schema → Dublin Core → CIDOC CRM** | c5 (25) | c35 (42) | 67 |
| 9 | **DataCite Metadata Schema → Dublin Core → MODS** | c5 (25) | c26 (37) | 62 |
| 10 | SPASE → Dublin Core → CIDOC CRM | c24 (14) | c35 (42) | 56 |
| 11 | SPASE → Dublin Core → MODS | c24 (14) | c26 (37) | 51 |
| 12 | EURISCO → ABCD → Darwin Core | c14 (34) | c1 (16) | 50 |
| 13 | OECD → ABCD → Darwin Core | c23 (24) | c1 (16) | 40 |
| 14 | MODS → Dublin Core → RIF-CS | c27 (27) | c32 (9) | 36 |
| 15 | **DataCite Metadata Schema → Dublin Core → RIF-CS** | c5 (25) | c32 (9) | 34 |
| 16 | HISPID → ABCD → Darwin Core | c18 (14) | c1 (16) | 30 |
| 17 | SPASE → Dublin Core → RIF-CS | c24 (14) | c32 (9) | 23 |

**Per-hop "missing" row counts** (from `comment.mapping_type == "missing"`, raw file rows, not inflated): c29=0/77, c37=0/49, c21=1/83, c32=0/8, c22=1/47, c20=0/40, c5=9/24 (notably high — over a third of c5's rows are semantically unmapped), c11=0/60, c13=0/37, c24=2/13, c27=1/26, c35=0/41, c26=1/36, c14=0/33, c1=0/15, c23=0/23, c18=0/13.

**Is DataCite → Dublin Core → DCAT-AP among these paths? No.** A search of all 24 node labels for "DCAT" found **zero matches — DCAT-AP does not exist as a node in this graph**. `c38` (the real DataCite→DCAT-AP/CiteDCAT-AP crosswalk) renders only as a DataCite-Metadata-Schema self-loop, never reaching a distinct DCAT-AP node, so this specific path cannot be represented structurally.

**Data-quality caveat:** the graph has **duplicate, un-deduplicated nodes** for the same real standards: `DataCite` (`datacite_4_4`, curated edge only) vs. `DataCite Metadata Schema` (`rdamsc_m11`, all rdamsc_cN edges), and `Dublin Core Terms` (`dublin_core_terms`, curated edge) vs. `Dublin Core` (`rdamsc_m15`, all rdamsc_cN edges). Paths 4, 8, 9, and 15 above (all "DataCite Metadata Schema → Dublin Core → X") are real 2-hop paths in the graph as built, but a reader might assume the curated `DataCite ↔ Dublin Core Terms` edge already covers this standard pair — it does not, because it connects a structurally separate pair of nodes. This should be flagged/fixed before the graph is used for path analysis in the paper.

---

## Artifacts produced by this audit (all untracked, none committed, `exports/sssom` untouched)

- `scripts/check_artifact_urls.py`
- `exports/pipeline/latest/rdamsc_artifacts_full.csv`, `exports/pipeline/latest/rdamsc_artifacts_full_summary.json`
- `exports/pipeline/strategies.csv`
- `AUDIT_REPORT_2026-09-29_freeze.md` (this file)

## Commands to reproduce

```bash
# Item 1
git status --short
git diff --stat -- exports/
git diff --stat -- exports/sssom/

# Item 2
uv run python scripts/check_artifact_urls.py \
  --output-csv exports/pipeline/latest/rdamsc_artifacts_full.csv \
  --output-summary exports/pipeline/latest/rdamsc_artifacts_full_summary.json

# Items 3-4: git-add provenance + content fingerprint
git log --follow --diff-filter=A --oneline -- exports/sssom/<file>.sssom.tsv
git show --stat <commit>
git show 5dc8e248:exports/pipeline/latest/rdamsc_crosswalks.csv
git show a1e6f99:exports/pipeline/latest/rdamsc_crosswalks.csv
# + a python script parsing the `comment` column of each *.sssom.tsv as JSON and reading `.notes`

# Item 5
# python: RDAMSCClient().get_mapping_detail("c12") for the unresolved pair
# + json.load(exports/graph/crosswalk_graph.json) for edge metadata

# Item 6
# python script over exports/graph/crosswalk_graph.json: build adjacency, enumerate 2-hop
# paths with no direct edge, sum rule_count per hop, sort descending
```
