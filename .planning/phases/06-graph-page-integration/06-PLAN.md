# Phase 06: Graph Page Integration — Plan

**Phase number:** 06
**Milestone:** v2.1 Unified Explorer — Graph + Stats Pages
**Status:** Planned
**Created:** 2026-08-25

## Summary

Port the existing GitLab Pages Cytoscape.js graph into the unified Vite+FastAPI app as a new `/graph` route, reusing the same data (`crosswalk_graph.json`) and behavior (including fullscreen mode) as the existing GitLab Pages explorer.

## Task Breakdown

### Task 1: Explore existing implementations

**Objective:** Understand the current graph implementations to identify reuse opportunities.

**Tasks:**
- Read `public/explorer/index.html` (GitLab Pages) — understand current Cytoscape setup
- Read `public/graph-visualizer/cytoscape_graph.html` — understand fullscreen mode
- Read `web/src/main.js` — understand current routing and navigation
- Check `public/data/` for `crosswalk_graph.json` location

**Deliverables:**
- Document reuse opportunities (shared Cytoscape component? shared data loading?)
- Document data path differences between GitLab Pages and Vite app

**Estimated effort:** 1 hour

---

### Task 2: Add Graph route to Vite app

**Objective:** Create `/graph` route in the Vite app.

**Tasks:**
- Add Graph button to navigation bar (Mappings, Graph, Stats, Convert)
- Create Graph component that loads and renders Cytoscape graph
- Implement fullscreen mode toggle
- Ensure data loads from `crosswalk_graph.json` (same path as GitLab Pages)

**Deliverables:**
- `/graph` route working in development (`npm run dev`)
- Graph renders identically to GitLab Pages
- Fullscreen mode works

**Estimated effort:** 2-3 hours

---

### Task 3: Add persistent navigation bar

**Objective:** Ensure navigation bar appears on every page.

**Tasks:**
- Update `main.js` to include Graph and Stats buttons
- Update navigation logic to handle Graph and Stats routes
- Ensure state (selected crosswalk, etc.) is preserved when navigating

**Deliverables:**
- Navigation bar shows (Mappings, Graph, Stats, Convert) on all pages
- User can navigate between pages without losing context

**Estimated effort:** 1 hour

---

### Task 4: Verify data consistency

**Objective:** Ensure graph data is consistent across deployments.

**Tasks:**
- Verify `crosswalk_graph.json` is in the same location for both GitLab Pages and Vite
- Run export script and verify graph data matches between deployments
- Check that no new CI jobs are needed in `.gitlab-ci.yml`

**Deliverables:**
- Data consistency verified
- `.gitlab-ci.yml` has exactly one `pages` job

**Estimated effort:** 1 hour

---

### Task 5: Create acceptance tests

**Objective:** Create tests that verify Phase 06 success criteria.

**Tasks:**
- Test `/graph` route renders graph
- Test fullscreen mode works
- Test `crosswalk_graph.json` loaded from expected path
- Test navigation bar appears on all pages
- Test navigation preserves state
- Test no additional CI jobs in `.gitlab-ci.yml`

**Deliverables:**
- Acceptance test suite
- Test results documented

**Estimated effort:** 1-2 hours

---

## Acceptance Criteria

- [ ] User can navigate to `/graph` and see the standards/crosswalks graph
- [ ] Graph data loads from `crosswalk_graph.json` (same file as GitLab Pages)
- [ ] Fullscreen mode works identically to GitLab Pages
- [ ] Persistent navigation bar appears on `/graph` page
- [ ] No additional CI jobs in `.gitlab-ci.yml` after merge
- [ ] Graph behaves identically to GitLab Pages (same data, same behavior)

## Blocking Risks

1. **Cytoscape.js duplication:** If the GitLab Pages Cytoscape implementation is tightly coupled to Pages deployment, porting may require significant refactoring
2. **Route conflicts:** The `/graph` route might conflict with existing Vite routes
3. **Data path differences:** If `crosswalk_graph.json` path differs between GitLab Pages and Vite, data loading may break
4. **Fullscreen API limitations:** Fullscreen mode may behave differently in the unified app vs Pages

## Success Indicators

- [ ] All 5 tasks completed
- [ ] All acceptance criteria met
- [ ] No blocking risks realized
- [ ] Phase 07 (Stats Page Integration) can begin immediately

## Dependencies

- Phase 05: Unified Vite+FastAPI app must be in place (already complete)

## Notes

- No backend API for graph data needed (static JSON only for v1)
- Reuse existing `graph-loader.js` if possible
- Must not add new CI jobs (GOV-02 requirement)
