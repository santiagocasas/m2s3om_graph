---
phase: 02
slug: static-frontend-data-export
# status lifecycle: draft (seeded by plan-phase) → validated (set by validate-phase §6)
# audit-milestone §5.5 distinguishes NOT-VALIDATED (draft) from PARTIAL (validated + nyquist_compliant: false) (#2117)
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-14
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (existing) |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `uv run --with pytest pytest tests/` |
| **Full suite command** | `uv run --with pytest pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run --with pytest pytest tests/` (quick) + Vite build smoke (`cd web && npm install && npm run build`)
- **After every plan wave:** Run `uv run --with pytest pytest` (full suite)
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | DATA-01 | T-02-01 / — | Export script runs without error and produces valid JSON with `standards[]`, `crosswalks[]`, `rules[]` | unit | `uv run python scripts/export_crosswalk_json.py && python -c "import json; d=json.load(open('public/data/crosswalk_graph.json')); assert 'standards' in d and 'crosswalks' in d; assert len(d['standards']) > 0; assert len(d['crosswalks']) > 0"` | ❌ new file needed | ⬜ pending |
| TBD | TBD | TBD | DATA-01 | T-02-01 / — | Exported JSON rules have all required fields | unit | `python -c "import json; d=json.load(open('public/data/crosswalk_graph.json')); rule=d['crosswalks'][0]['rules'][0]; required=['source_paths','target_paths','mapping_type','confidence','semantic_loss','ambiguity','strategy']; assert all(k in rule for k in required)"` | ✅ in same test | ⬜ pending |
| TBD | TBD | TBD | WEB-01 | — | Vite build produces `dist/` with `index.html` | smoke | `cd web && npm install && npm run build && test -f dist/index.html` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | WEB-01 | — | `dist/` copied into `public/explorer/` | integration | `test -f public/explorer/index.html` | ✅ part of CI merge | ⬜ pending |
| TBD | TBD | TBD | WEB-02 | — | `.gitlab-ci.yml` has exactly one `pages` job | lint | `grep -c '^pages:' .gitlab-ci.yml` returns 1 | ✅ part of CI merge | ⬜ pending |
| TBD | TBD | TBD | GOV-01 | — | No runtime imports from `claude_suggestions/` in web/ | lint | `grep -r 'claude_suggestions' web/src/` returns empty | ✅ part of scaffold integration | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_export_crosswalk_json.py` — stubs for DATA-01 export script validation
- [ ] `tests/test_vite_smoke.py` — runs `cd web && npm install && npm run build` and checks `dist/`
- [ ] Framework install: `npm install -D vite` (no extra Python test framework; uses existing pytest)

---

## Manual-Only Verifications

*None: All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
