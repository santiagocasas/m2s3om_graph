# RDAMSC → SSSOM Paper Audit

**Date:** 2026-09-29
**Repo:** `/home/casas/AI/m2s3om_graph`, HEAD `401bbb0` (working tree dirty — `paper/**`, `README.md`, `.gitlab-ci.yml`, `provenance.ttl`, `web/**` modified; `paper/figures/`, `paper/main.pdf` untracked)

**Scope note:** The "paper" audited here is the uncommitted working tree (`paper/**`), not a commit. Per the requester's instructions:
- `make pipeline-run-freeze` was **not** run (would rewrite `.local/`, `exports/sssom`, `exports/pipeline/latest`).
- `pytest`/coverage was **not** run live (not approved) — item 12 is read from stored artifacts only.
- The n=1000 OAI benchmark **was** rerun live (approved) — see item 11.
- All read-only script outputs are in `/tmp/opencode/audit/` (this directory).

**Key structural finding:** Items 1–7 trace almost exactly to one specific historical commit, **`5dc8e248`** ("chore(exports): freeze updated RDAMSC SSSOM and analytics snapshot", **2026-03-05**, not May as assumed). That commit's own `rdamsc_crosswalks.csv` / `rdamsc_artifacts.csv` reproduce the paper's 19/11/7, 45/32/13, and host-failure counts exactly. Items 4/5/8 reproduce exactly at HEAD only after excluding two files (`rdamsc_c19`, `rdamsc_c29`) added later by commit `a592f22` (2026-08-17).

---

## Table: item | paper value | recomputed | match | command / source / commit

| # | Item | Paper value | Recomputed | Match | Command / source / commit |
|---|---|---|---|---|---|
| 1a | Crosswalks total | 37 | **37** | ✅ | `git show 5dc8e248:exports/pipeline/latest/rdamsc_crosswalks.csv` → 37 rows. Constant at HEAD too. |
| 1b | Distinct standards | 44 | **NOT reproducible** — naive parse gives 32 | ❌ | Regex split of `name` col on `_TO_`/" to " across 37 rows at `5dc8e248`; 3 rows unparseable (`c1`="One", `c2`="Two", `c38`=single self-referential name). No RDAMSC catalog sync JSON exists anywhere in repo (`data/` only has `crosswalks.human.json`, which covers 20–24 nodes, not all 37 attempted pairs). Graph-node counts (20 old / 24 current) are also far below 44. |
| 2 | Outcome per crosswalk: 19/11/7 | 19 ready / 11 unreachable / 7 failed_parse | **19/11/7 exact** | ✅ | `git show 5dc8e248:exports/pipeline/latest/rdamsc_crosswalks.csv`, `Counter(status)`. **Ready (19):** c1,c2,c5,c11,c13,c14,c20,c21,c22,c24,c26,c27,c30,c32,c33,c35,c36,c37,c38. **Unreachable (11):** c4,c6,c7,c8,c9,c10,c12,c15,c16,c17,c31. **Failed_parse (7):** c3,c18,c19,c23,c28,c29,c34. Caveat: at this same commit, `c1`/`c2` are marked "ready" but have **no `.sssom.tsv` file in the tree** — a status/artifact inconsistency in the paper's own source commit. |
| 3 | Artifact URLs: 45 checked / 32 fetched / 13 failed; NOAA 4, GCMD 3, datacite.org 3 | as stated | **Exact match** | ✅ | `git show 5dc8e248:exports/pipeline/latest/rdamsc_artifacts.csv` (45 rows). `Counter(status)={ready:23, failed_unreachable:13, failed_parse:9}`; fetched=45−13=32. Host failures: `service.ncddc.noaa.gov`=4, `gcmd.nasa.gov`=3, `schema.datacite.org`=3 (plus `www.loc.gov`=4, `www.bgbm.org`=2, 5 hosts×1). **Not reproducible at HEAD**: current `rdamsc_artifacts.csv` has only 24 rows (bookkeeping never carried forward through later runs); NOAA count there has drifted to 5. |
| 4 | SSSOM files: 24, 993 rows; curated DataCite↔DC = 110 rows | as stated | **993/24 exact only when c19,c29 excluded**; HEAD has 26 files/1072 rows | ⚠️ (matches an earlier state, not HEAD) | Python script over `exports/sssom/*.sssom.tsv` (skip `#` header lines, `csv.DictReader`). HEAD: 26 files, 1072 rows. Excluding `rdamsc_c19.sssom.tsv`+`rdamsc_c29.sssom.tsv` → 24 files, 993 rows — exact match. `datacite44_to_dcterms.sssom.tsv` = 110 rows, exact match. `git log --follow` on c19/c29 shows both added by commit **`a592f22`** ("feat: add deployment templates and crosswalk fixtures", 2026-08-17) — this is the commit boundary where the paper's snapshot diverges from HEAD. **Mismatch reconciled**: 19 ready ids (at 5dc8e248) − 1 (c2, no file) + 5 stale-status-but-real-file ids (c3,c18,c23,c28,c34, marked failed_parse yet holding real rows) = 23 rdamsc files + 1 curated = 24. |
| 5 | Predicates: exactMatch 800, relatedMatch 152, broadMatch 28, narrowMatch 13 | as stated | **Exact match**, same 24-file subset | ✅ | Same script, `Counter(predicate_id)`. broadMatch/narrowMatch identical at HEAD too (c19/c29 contributed 0 to those). `decomposition`→`narrowMatch`: confirmed in code — `MappingType.DECOMPOSITION` (`src/m2s3om_graph/db/models.py:16`) maps to `skos:narrowMatch` (`src/m2s3om_graph/sssom.py:45`), and `decomposition` is listed in the LLM prompt (`src/m2s3om_graph/rdamsc/llm_extract.py:233`). |
| 6 | LLM runs 20 / deterministic 2; 8 zero-yield LLM runs; 19 processed | 20/2, 8 zero-yield | **20/2 exact; zero-yield = 7, not 8** | ⚠️ | `Counter(strategy)` over all 37 rows at `5dc8e248` = `{llm:20, deterministic_generic:2, '':15}`. Ready breakdown: llm=13, deterministic_generic=2 (c36,c38), blank=4 (c1,c2,c5,c11). All 7 `failed_parse` rows have `strategy='llm'`, `reason='no_rules_extracted'` → 13+7=20 llm runs, **7** (not 8) returned zero rows. Off by one from the paper; no 8th zero-yield run visible in any snapshot. |
| 7 | Deterministic threshold ≥8 | 8 | **Confirmed in code**; threshold sweep not reproducible | ⚠️ | `DETERMINISTIC_GENERIC_MIN_RULES = 8` at `src/m2s3om_graph/rdamsc/ingest.py:41` (HEAD). Sweep at 4/6/8/12 needs per-crosswalk deterministic-candidate counts; only 2 crosswalks (c19, c29) retain this diagnostic in the live status file, both with 0 candidates before/after dedupe — insensitive to any threshold. No data for the other 35. |
| 8 | Graph: 20 standard nodes / 23 crosswalk edges | 20/23 | **Exact match to the old export; HEAD has 24/26** | ⚠️ (matches an earlier state, not HEAD) | `data/crosswalks.human.json` (frozen 2026-05-29, commit `c8bdcb03e`): 20 nodes, 23 edges; `Counter(relationship)={LLM extraction:21, Deterministic extraction:2}`. Deterministic edges: `rdamsc_c36` (EAD→CIDOC CRM), `rdamsc_c38` (DataCite self-loop). 24 sssom files − 1 (c5 merged into the curated DataCite→DC edge, per `merged_crosswalk_ids`) = 23. **`exports/graph/crosswalk_graph.json` at HEAD (commit `f8de73b7`, "add canonical graph edge metadata", 2026-08-27) is newer/richer: 24 nodes, 26 edges** — c5, c19, c29 kept as their own edges, no merge. This is a genuine drift: the paper's 20/23 matches the deployed (older, duplicated 7× under `web/`, `public/`) export, not the current canonical one. |
| 9 | Doc sizes: median 27k, mean 60k, p90 134k; 3 docs hit 140k cap; 200k conversion cap | as stated | **NOT reproducible** | ❌ | No runtime log was ever persisted at any commit: `exports/pipeline/latest/pipeline.log` is an identical 3-line placeholder both at HEAD and at `5dc8e248` ("No persisted pipeline runtime log was found..."). Per-document char counts only exist for the 2 crosswalks reprocessed after the last freeze (c19: 11,510 chars; c29: 49,822 chars) — far too few for any percentile. Caps confirmed in code: `max_chars=140_000` (`rdamsc/ingest.py:216,297`), `max_chars=200_000` (`rdamsc/artifacts.py:322`), but note the c19/c29 diagnostics record `llm_diagnostics.max_input_chars=120000`, not 140,000 — an unreconciled discrepancy between stored diagnostics and the current code constant. |
| 10 | Models: Ministral-3-14B via alias-fast, Qwen3.5-122B | as stated | **NOT supported by any artifact** | ❌ | `grep -r "Qwen\|Ministral" src/` → zero matches. Only generic default `DEFAULT_LLM_MODEL="alias-fast"` exists (`rdamsc/llm_runtime.py:7`, `config/settings.py:23`). `generation_manifest.json.environment.M2S3OM_LLM_MODEL=""` (unset) at freeze time. No manifest, log, or diagnostic field records an actual model name anywhere. |
| 11 | Benchmark: 85.7%/79.2% (n=1, paper); 75.2% (n=1000, poster) | as stated | **Neither reproducible** — 0%/0% (n=1, stored); ~30.9%/16.7% (n=1000, stored, and consistent on 2 separate reruns) | ❌ | Formulas read from `src/m2s3om_graph/benchmark/metrics.py`: `field_coverage = |expected∩actual fields| / |expected fields|`; `value_overlap` = mean over the union of fields of (matched normalized values / expected normalized values), normalization = lowercase + whitespace-collapse + strip chars outside `[a-z0-9:/._ -]`. Stored `exports/benchmark/datacite_dc_oai_hzi_benchmark.json` (n=1, commit `65bcbce`): `avg_field_coverage=0.0, avg_value_overlap=0.0`. Stored `exports/benchmark/datacite_dc_oai_awi_benchmark.json` (n=1000, commit `f316ab5`, 2026-05-31): `avg_field_coverage=0.3086, avg_value_overlap=0.1674`. **Live rerun #1** (this session, commit `401bbb0`): `--limit 1000` → `{cases:1000, avg_field_coverage:0.30867, avg_value_overlap:0.16742, failures:8}`, completed in ~850s. **Reproducibility caveat**: when the user independently ran the identical `--limit 1000` command afterward, it produced **no output and hung indefinitely** (Ctrl+C required, stack trace stuck inside `ssl.SSLSocket.do_handshake` for a single record's `GetRecord` call). A follow-up **live rerun #2, `--limit 10`** (diagnostic, ~5s, `/tmp/opencode/audit/bench_diag`) succeeded cleanly: `{cases:10, avg_field_coverage:0.3088, avg_value_overlap:0.1677, failures:0}` — consistent with the n=1000 figures, confirming AWI is reachable and the mapping/metrics code path is correct. Root cause of the hang is in `src/m2s3om_graph/oai/client.py:12` (`requests.get(..., timeout=self.timeout_s)`) combined with `scripts/run_datacite_dc_benchmark.py`'s `_run_oai_pair_benchmark` (lines 97–127): the per-request timeout is passed through, but the script prints **zero progress output** during the ~2000-request loop, and a stalled TCP/TLS handshake to `epic.awi.de` was observed to sit well past the nominal 20s in practice. **Conclusion: the ~30.9%/16.7% n=1000 figure is reproducible in substance (2 successful full/partial runs agree), but the exact `--limit 1000` command is not reliably reproducible on demand** — it depends on live network/server conditions outside this repo's control, and the paper/poster numbers (85.7/79.2, 75.2%) remain unsupported regardless. |
| 12a | Tests: 113 | 113 | **NOT confirmed** — static count 168 | ❌ | `grep -rc "^def test_" tests/*.py` (47 files) = 168 at HEAD. Live `pytest --collect-only` not approved, so an authoritative count wasn't taken. 168 ≫ 113; the paper's number likely predates substantial test growth. |
| 12b | Coverage: 74% | 74% | **74% — matches, but from a stale/unrelated artifact** | ⚠️ | Stored `htmlcov/class_index.html` (gitignored, untracked, filesystem mtime 2026-05-27) contains `pc_cov">74%`. Not attributable to any git commit and not regenerated live in this audit (not approved). |
| 12c | "Known open defect": missing fastapi dependency in `tests/test_suggest_api.py` | open defect | **Resolved, not open at HEAD** | ❌ | `pyproject.toml:16` lists `fastapi>=0.110` as a required (not optional) dependency; `uv.lock` resolves fastapi 0.141.1. `git log --all -S "fastapi>=0.110" -- pyproject.toml` → commit **`ace6dab`** "fix: declare fastapi/uvicorn/httpx2 deps and restore fail-closed UI copy" is the exact fix. Target module `claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/main.py` exists and has a compiled `.pyc`. |
| 13 | Evidence-snippet verbatim rate | (unspecified rate) | **NOT reproducible** | ❌ | No converted source-chunk text is persisted anywhere in the repo outside SurrealDB's binary RocksDB-style files (`.local/surrealdb/*.sst,*.blob,...`), which were not queried for this item. SSSOM rows only carry short freeform `evidence` strings (`rdamsc/llm_extract.py` lines 54,81,180,188,236,289), not the chunk they were drawn from. Would require either a live SurrealDB chunk query or a fresh re-fetch/re-convert of all 45 artifact URLs. |

---

## (a) Paper statements not supported by current artifacts

1. **44 distinct standards** (item 1) — no source enumerates this; best reconstruction is 32.
2. **Document-size percentiles and 140k-cap hit count = 3** (item 9) — no log or per-document data exists to compute this at all.
3. **Model identities "Ministral-3-14B via alias-fast, Qwen3.5-122B"** (item 10) — zero occurrences of either model name anywhere in the codebase; only a generic default alias is evidenced.
4. **Benchmark 85.7%/79.2% on a single record** (item 11) — the only stored single-record run scores 0%/0%.
5. **Poster's 75.2% on n=1000** (item 11) — stored and freshly rerun n=1000 results give ~30.9%/16.7%, not 75.2% on either metric.
6. **113 tests** (item 12a) — static count is 168; unverifiable exactly without a live pytest run.
7. **"Known open defect": missing fastapi dependency** (item 12c) — fixed by commit `ace6dab`; not open at HEAD.
8. **Evidence-snippet verbatim-occurrence rate** (item 13) — no artifact retains the data needed to compute it.
9. Secondary/structural: the paper's item-2 source commit (`5dc8e248`) itself marks `c1`/`c2` "ready" with no corresponding `.sssom.tsv` files in the tree at that commit — an internal inconsistency in the paper's own primary source, not a repo-wide claim but worth flagging.
10. **Script robustness gap found during this audit (not a paper claim, but affects how item 11's number should be cited):** `scripts/run_datacite_dc_benchmark.py --mode oai --discover --limit 1000` produces no progress output while making ~2000 sequential HTTP requests, and was observed to hang indefinitely on a stalled TLS handshake despite `--timeout 20` being passed through to `requests.get()` (`src/m2s3om_graph/oai/client.py:12`). The command is not safe to cite as "rerun on demand" without a retry/backoff and progress-logging fix; the underlying ~30.9%/16.7% figure is corroborated by a stored run, one full live rerun, and one clean `--limit 10` diagnostic rerun, but not by a guaranteed-repeatable single command.

---

## (b) Numbers that changed since the frozen run, with the commit that produced the current value

| Item | Frozen value (commit, date) | Current value (commit, date) | Cause |
|---|---|---|---|
| Items 2, 6 (19/11/7 ready-split; 20 llm/2 det.) | `5dc8e248`, 2026-03-05 | HEAD `.local` status: 25 ready/12 unreachable (no failed_parse tracked); manifest at `33078ce`→`a1e6f99`, 2026-06-02: 23/11/3 | Later pipeline reruns processed more crosswalks and the failure taxonomy drifted; status bookkeeping was only partially regenerated. |
| Item 3 (45/32/13, host counts) | `5dc8e248`, 2026-03-05 | HEAD `rdamsc_artifacts.csv`: only 24 rows, NOAA count 5 not 4 | Later runs (`a1e6f99`, `a592f22`) only recorded artifacts for the crosswalks they actually touched, not a full 45-row resweep — older rows were never carried forward. |
| Items 4, 5 (24 files/993 rows) | pre-`a592f22` state | HEAD: 26 files/1072 rows | Commit **`a592f22`** ("feat: add deployment templates and crosswalk fixtures", 2026-08-17) added `rdamsc_c19.sssom.tsv` and `rdamsc_c29.sssom.tsv`. |
| Item 8 (20 nodes/23 edges) | `data/crosswalks.human.json`, commit **`c8bdcb03e`**, 2026-05-29 | `exports/graph/crosswalk_graph.json`, commit **`f8de73b7`**, 2026-08-27: 24 nodes/26 edges | Newer canonical graph export stopped merging c5 into the curated DataCite→DC edge and added c19/c29 as edges; `data/crosswalks.human.json` (still served under `web/`, `public/`, etc., 7 copies) was never regenerated from it. |
| Item 12b (74% coverage) | `htmlcov/`, filesystem mtime 2026-05-27, no commit (gitignored) | unknown at HEAD (168 tests present, not measured live) | Test suite grew substantially (168 vs whatever ran under the 74% snapshot) after coverage was last captured; no commit ties the two. |

Baseline used for this comparison, per the requester's direction: manifest run `a1e6f99` (embedded in `generation_manifest.json`, generated 2026-06-02T16:22:57Z, tagged "add poster files" in `git log`) — note this run is dated **June**, not May, and its own summary (23/11/3) does not match the paper's 19/11/7 either; the paper's actual numeric source is the earlier commit `5dc8e248` (2026-03-05).

---

## (c) Single command sequence to regenerate all of these numbers against one frozen commit

```bash
# 1. Freeze a fresh pipeline run (writes .local/, exports/sssom, exports/pipeline/latest — NOT run in this audit)
make pipeline-run-freeze

# 2. Emit stats/CSVs/plots from that freeze
make pipeline-stats   # or: PIPELINE_EXPORT_DIR=<dir> make pipeline-stats

# 3. Derived file/predicate/graph counts (script written for this audit; not part of repo)
python3 - <<'PY'
# iterate exports/sssom/*.sssom.tsv -> file count, row count, predicate_id Counter
# iterate exports/graph/crosswalk_graph.json -> node/edge counts
PY

# 4. Benchmark (single-record + n=1000)
uv run python scripts/run_datacite_dc_benchmark.py --mode oai --institution HZI --discover --limit 1 --output-dir exports/benchmark
uv run python scripts/run_datacite_dc_benchmark.py --mode oai --institution AWI --discover --limit 1000 --timeout 20 --output-dir exports/benchmark

# 5. Tests + coverage
uv run --with pytest --with pytest-cov pytest --cov=src --cov-report=html --collect-only -q   # count
uv run --with pytest --with pytest-cov pytest --cov=src --cov-report=html                      # coverage %

# 6. Record the commit this all ran against
git rev-parse HEAD > exports/pipeline/latest/frozen_commit.txt
```

Items 1 (44 standards), 9 (doc-size percentiles/cap hits), 10 (model aliases) and 13 (evidence verbatim rate) **cannot** be added to this sequence without also changing the pipeline to persist data it currently discards: a catalog-level standards list, per-document char/cap telemetry, per-run model identity, and per-rule source-chunk text. Those are code changes, not audit commands.

---

## Appendix: exact commands run per item

All commands below were run read-only from repo root (`/home/casas/AI/m2s3om_graph`), output redirected to `/tmp/opencode/audit/`. Git one-liners are verbatim. Python blocks marked "(inline)" reproduce, statement-for-statement, the ad-hoc scripts actually executed against the CSV/TSV/JSON files during the audit; re-running them against the same commits reproduces the same numbers.

### Items 1, 2, 6, 7 — crosswalk status/strategy counts at the paper's source commit

```bash
git show 5dc8e248:exports/pipeline/latest/rdamsc_crosswalks.csv > /tmp/opencode/audit/crosswalks_5dc8e248.csv
```

```python
# (inline) — item 1a/2/6/7: status + strategy Counters, ready/unreachable/failed_parse id lists
import csv
from collections import Counter

rows = list(csv.DictReader(open("/tmp/opencode/audit/crosswalks_5dc8e248.csv")))
print("total rows:", len(rows))                                   # -> 37   (item 1a)
print("status:", Counter(r["status"] for r in rows))               # -> {ready:19, failed_unreachable:11, failed_parse:7}  (item 2)
print("strategy:", Counter(r["strategy"] for r in rows))           # -> {llm:20, deterministic_generic:2, '':15}           (item 6)

for status in ("ready", "failed_unreachable", "failed_parse"):
    ids = [r["crosswalk_id"].replace("rdamsc_", "") for r in rows if r["status"] == status]
    print(status, sorted(ids, key=lambda x: int(x[1:])))

# item 6 zero-yield LLM runs = failed_parse rows whose strategy is llm
zero_yield = [r["crosswalk_id"] for r in rows if r["status"] == "failed_parse" and r["strategy"] == "llm"]
print("zero-yield llm runs:", len(zero_yield), zero_yield)         # -> 7 (not paper's 8)
```

```bash
# item 1b: naive standards-name parse (undercounts; documented as such)
python3 - <<'PY'
import csv, re
rows = list(csv.DictReader(open("/tmp/opencode/audit/crosswalks_5dc8e248.csv")))
names = set()
unparsed = []
for r in rows:
    n = r["name"]
    parts = re.split(r"_TO_| to |_to_", n)
    if len(parts) == 2:
        names.update(p.strip() for p in parts)
    else:
        unparsed.append((r["crosswalk_id"], n))
print(len(names), sorted(names))
print("unparsed:", unparsed)   # -> c1="One", c2="Two", c38 self-referential
PY
```

```bash
# item 7: deterministic threshold constant, confirmed in code at HEAD
grep -n "DETERMINISTIC_GENERIC_MIN_RULES" src/m2s3om_graph/rdamsc/ingest.py
# -> src/m2s3om_graph/rdamsc/ingest.py:41:DETERMINISTIC_GENERIC_MIN_RULES = 8
```

### Item 3 — artifact URLs, fetch outcomes, host failure counts

```bash
git show 5dc8e248:exports/pipeline/latest/rdamsc_artifacts.csv > /tmp/opencode/audit/artifacts_5dc8e248.csv
```

```python
# (inline)
import csv
from collections import Counter
from urllib.parse import urlparse

rows = list(csv.DictReader(open("/tmp/opencode/audit/artifacts_5dc8e248.csv")))
print("total:", len(rows))                                    # -> 45
status = Counter(r["status"] for r in rows)
print(status)                                                  # -> {ready:23, failed_unreachable:13, failed_parse:9}
print("fetched:", len(rows) - status["failed_unreachable"])    # -> 32

hosts = Counter(urlparse(r["url"]).netloc for r in rows if r["status"] == "failed_unreachable")
print(hosts.most_common())
# -> service.ncddc.noaa.gov:4, gcmd.nasa.gov:3, schema.datacite.org:3, www.loc.gov:4, www.bgbm.org:2, 5x1
```

```bash
# current-HEAD comparison (shows drift — only 24 rows, NOAA=5)
python3 - <<'PY'
import csv
from collections import Counter
from urllib.parse import urlparse
rows = list(csv.DictReader(open("exports/pipeline/latest/rdamsc_artifacts.csv")))
print(len(rows), Counter(r["status"] for r in rows))
print(Counter(urlparse(r["url"]).netloc for r in rows if r["status"] == "failed_unreachable"))
PY
```

### Items 4, 5 — SSSOM file/row/predicate counts, curated-file row count

```bash
# (inline) run over the live directory at HEAD, then repeated excluding c19/c29
python3 - <<'PY'
import csv, glob
from collections import Counter

def load(path):
    with open(path) as f:
        lines = [l for l in f if not l.startswith("#")]
    return list(csv.DictReader(lines, delimiter="\t"))

files = sorted(glob.glob("exports/sssom/*.sssom.tsv"))
total_rows = 0
predicate_counter = Counter()
per_file = {}
for fp in files:
    rows = load(fp)
    per_file[fp] = len(rows)
    total_rows += len(rows)
    predicate_counter.update(r["predicate_id"] for r in rows)

print("files:", len(files))                    # -> 26 at HEAD
print("total rows:", total_rows)                # -> 1072 at HEAD
print("predicates:", predicate_counter)         # -> {exactMatch:844, relatedMatch:187, broadMatch:28, narrowMatch:13}
print("curated file rows:", per_file["exports/sssom/datacite44_to_dcterms.sssom.tsv"])   # -> 110

excluded = {"exports/sssom/rdamsc_c19.sssom.tsv", "exports/sssom/rdamsc_c29.sssom.tsv"}
files2 = [f for f in files if f not in excluded]
total2 = sum(per_file[f] for f in files2)
pred2 = Counter()
for fp in files2:
    pred2.update(r["predicate_id"] for r in load(fp))
print("files (excl. c19/c29):", len(files2))    # -> 24
print("total rows (excl.):", total2)            # -> 993, exact match to paper
print("predicates (excl.):", pred2)             # -> {exactMatch:800, relatedMatch:152, broadMatch:28, narrowMatch:13}, exact match
PY
```

```bash
# commit boundary for c19/c29
git log --follow --oneline -- exports/sssom/rdamsc_c19.sssom.tsv
git log --follow --oneline -- exports/sssom/rdamsc_c29.sssom.tsv
# both -> a592f22 "feat: add deployment templates and crosswalk fixtures" (2026-08-17), parent 7753de3
```

```bash
# decomposition -> narrowMatch, confirmed in code
grep -n "DECOMPOSITION" src/m2s3om_graph/db/models.py
grep -n "narrowMatch" src/m2s3om_graph/sssom.py
grep -n "decomposition" src/m2s3om_graph/rdamsc/llm_extract.py
```

### Item 8 — graph node/edge counts

```python
# (inline) — old (deployed) graph
import json
g = json.load(open("data/crosswalks.human.json"))
print("nodes:", len(g["nodes"]))          # -> 20
print("edges:", len(g["edges"]))          # -> 23
from collections import Counter
print(Counter(e["relationship"] for e in g["edges"]))   # -> {LLM extraction:21, Deterministic extraction:2}

# (inline) — current canonical export
g2 = json.load(open("exports/graph/crosswalk_graph.json"))
print("nodes:", len(g2["nodes"]))         # -> 24
print("edges:", len(g2["edges"]))         # -> 26
```

```bash
git log --oneline -1 -- data/crosswalks.human.json        # -> c8bdcb03e ... 2026-05-29
git log --oneline -1 -- exports/graph/crosswalk_graph.json  # -> f8de73b7 ... 2026-08-27
diff <(git show c8bdcb03e:data/crosswalks.human.json) exports/graph/crosswalk_graph.json > /tmp/opencode/audit/graph_diff.txt
```

### Item 9 — document size / cap-hit evidence (negative result)

```bash
diff <(git show 5dc8e248:exports/pipeline/latest/pipeline.log) exports/pipeline/latest/pipeline.log
# -> no difference; both are the 3-line placeholder, no real runtime log ever existed
grep -n "max_chars" src/m2s3om_graph/rdamsc/ingest.py src/m2s3om_graph/rdamsc/artifacts.py
# -> ingest.py:216,297: max_chars: int = 140_000 ; artifacts.py:322: max_chars: int = 200_000
python3 - <<'PY'
import json
s = json.load(open(".local/rdamsc_pipeline_status.json"))
for k, v in s.items():
    dd = v.get("result", {}).get("deterministic_diagnostics")
    if dd:
        print(k, dd.get("total_chars"), dd.get("normalized_chars"))
PY
# -> only rdamsc_c19 (11510) and rdamsc_c29 (49822) have any char-count data
```

### Item 10 — model identity search (negative result)

```bash
grep -rn "Qwen\|Ministral" src/                    # -> no matches
grep -n "DEFAULT_LLM_MODEL" src/m2s3om_graph/rdamsc/llm_runtime.py src/m2s3om_graph/config/settings.py
# -> llm_runtime.py:7: DEFAULT_LLM_MODEL = "alias-fast" ; settings.py:23: os.getenv("M2S3OM_LLM_MODEL", "alias-fast")
python3 -c "import json; print(json.load(open('exports/sssom/generation_manifest.json'))['environment'].get('M2S3OM_LLM_MODEL'))"
# -> "" (unset at freeze time)
```

### Item 11 — DataCite→DC benchmark coverage/overlap

```bash
sed -n '1,116p' src/m2s3om_graph/benchmark/metrics.py   # field_coverage / value_overlap formulas (quoted in report body)
python3 -c "import json; d=json.load(open('exports/benchmark/datacite_dc_oai_hzi_benchmark.json')); print(d['avg_field_coverage'], d['avg_value_overlap'])"
# -> 0.0 0.0   (stored n=1 HZI run, commit 65bcbce)
python3 -c "import json; d=json.load(open('exports/benchmark/datacite_dc_oai_awi_benchmark.json')); print(d['cases'], d['avg_field_coverage'], d['avg_value_overlap'])"
# -> 1000 0.30856 0.16736   (stored n=1000 AWI run, commit f316ab5, 2026-05-31)
curl -s "https://epic.awi.de/cgi/oai2?verb=Identify"   # reachability check before live rerun
uv run python scripts/run_datacite_dc_benchmark.py --mode oai --institution AWI --discover --limit 1000 --timeout 20 --output-dir /tmp/opencode/audit/bench
# -> fresh (live rerun #1, this session): {cases:1000, avg_field_coverage:0.30866783380018675, avg_value_overlap:0.16741527777777776, failures:8}, ~850s
```

**Reproducibility caveat (added after user independently reran the command):** the user ran the identical `--limit 1000` command and it hung indefinitely with no output (Ctrl+C required; traceback stuck in `ssl.SSLSocket.do_handshake` inside `client.get_record()`). Diagnostic follow-up:

```bash
time uv run python scripts/run_datacite_dc_benchmark.py --mode oai --institution AWI --discover --limit 10 --timeout 20 --output-dir /tmp/opencode/audit/bench_diag
# -> {cases:10, avg_field_coverage:0.3088235294117647, avg_value_overlap:0.16769005847953217, failures:0}
# real 0m5.222s -- AWI reachable and fast for a small sample; confirms code path is correct
grep -n "requests.get" src/m2s3om_graph/oai/client.py   # line 12: timeout=self.timeout_s is passed through correctly
sed -n '97,127p' scripts/run_datacite_dc_benchmark.py   # confirms zero progress output/logging during the ~2000-request loop
```
Conclusion: the ~30.9%/16.7% figure is corroborated (stored run + full live rerun + clean n=10 diagnostic), but the exact `--limit 1000` invocation is not guaranteed to complete on any given attempt — it has no progress indicator and no evidence the per-request timeout reliably bounds a stalled TLS handshake in this environment. Do not cite "rerun the command below" as a guaranteed-repeatable check for this number without first patching `oai/client.py`/`run_datacite_dc_benchmark.py` for progress logging and connect-timeout robustness.

### Item 12 — tests, coverage, fastapi defect

```bash
grep -rc "^def test_" tests/*.py | awk -F: '{s+=$2} END{print s}'    # -> 168 at HEAD (static grep, not pytest collection)
grep -o 'pc_cov">[0-9]*%' htmlcov/class_index.html                    # -> pc_cov">74%  (stored, mtime 2026-05-27, gitignored)
grep -n "fastapi" pyproject.toml                                      # -> line 16: "fastapi>=0.110", inside [project] deps, not optional
git log --all -S "fastapi>=0.110" -- pyproject.toml --oneline         # -> ace6dab "fix: declare fastapi/uvicorn/httpx2 deps and restore fail-closed UI copy"
ls -la claude_suggestions/m2s3om-suggest-api/m2s3om-suggest-api/       # -> main.py present, main.cpython-312.pyc present
```

### Item 13 — evidence-snippet source location (negative result)

```bash
find . -iname '*chunk*' -not -path './.venv/*'     # -> no persisted converted-chunk text anywhere
ls -la .local/                                      # -> rdamsc_plots/, rdamsc_artifacts.csv, rdamsc_crosswalks.csv,
                                                     #    rdamsc_stats_summary.json, surrealdb/ (binary), rdamsc_pipeline_status.json
grep -n "evidence" src/m2s3om_graph/rdamsc/llm_extract.py   # -> lines 54,81,180,188,236,289: evidence is a short freeform
                                                              #    LLM-written string, no source-chunk artifact retained per rule
```
