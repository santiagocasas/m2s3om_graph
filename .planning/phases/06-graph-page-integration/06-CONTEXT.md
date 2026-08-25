# Phase 06: Graph Page Integration — Context

**Phase number:** 06
**Milestone:** v2.1 Unified Explorer — Graph + Stats Pages
**Status:** Planning
**Created:** 2026-08-25

## Objective

Port the existing GitLab Pages Cytoscape.js graph (standards/crosswalks explorer) into the unified Vite+FastAPI app as a new `/graph` route, reusing the same data and behavior (including fullscreen mode) as the existing GitLab Pages explorer.

## Key Requirements

| Requirement | Description |
|-------------|-------------|
| GRAPH-01 | User can open the unified explorer graph page at `/graph` showing the standards/crosswalks graph built with Cytoscape.js, reusing the same data and behavior (including fullscreen mode) as the existing GitLab Pages explorer. |
| GRAPH-02 | The /graph route loads Cytoscape graph data from the same static JSON file that GitLab Pages uses (`crosswalk_graph.json`), ensuring consistency across deployments. |
| NAV-01 | The unified explorer has a persistent navigation bar on every page (Mappings, Graph, Stats, Convert) allowing users to switch between routes without losing context. |
| DATA-02 | Both /graph and /stats routes consume the same pre-exported static JSON/assets that GitLab Pages uses, avoiding duplicate export steps and ensuring consistency. |
| GOV-02 | The .gitlab-ci.yml still contains exactly one `pages` job after the merge, with no additional CI jobs required for the new routes. |

## Scope

### In Scope
- New `/graph` route in Vite app (frontend routing)
- Cytoscape.js graph rendering component
- Data loading from `crosswalk_graph.json` (same as GitLab Pages)
- Fullscreen mode toggle
- Persistent navigation bar (Mappings, Graph, Stats, Convert)
- Share code with existing GitLab Pages Cytoscape implementation (DRY)

### Out of Scope
- Backend API for graph data (static JSON only for v1)
- Dynamic graph generation or transformation
- Real-time graph updates
- Customization of graph layout or appearance beyond existing implementation

## Known Constraints

- The graph data must come from the same `crosswalk_graph.json` file that GitLab Pages uses
- No new CI jobs allowed — must reuse existing `pages` job
- Must reuse existing Cytoscape.js implementation as much as possible
- No backend endpoints unless statically impossible

## Success Criteria

- [ ] User can navigate to `/graph` and see the standards/crosswalks graph
- [ ] Graph data loads from `crosswalk_graph.json` (same file as GitLab Pages)
- [ ] Fullscreen mode works identically to GitLab Pages
- [ ] Persistent navigation bar appears on `/graph` page
- [ ] No additional CI jobs in `.gitlab-ci.yml` after merge
- [ ] Graph behaves identically to GitLab Pages (same data, same behavior)

## Blocking Risks

1. **Cytoscape.js duplication**: If the GitLab Pages Cytoscape implementation is tightly coupled to Pages deployment, porting may require significant refactoring
2. **Route conflicts**: The `/graph` route might conflict with existing Vite routes
3. **Data path differences**: If `crosswalk_graph.json` path differs between GitLab Pages and Vite, data loading may break
4. **Fullscreen API limitations**: Fullscreen mode may behave differently in the unified app vs Pages

## Decision Log

| Decision | Rationale | Owner | Date |
|----------|-----------|-------|------|
| Use existing `crosswalk_graph.json` | Reuse same data source as GitLab Pages (DATA-02) | AI | 2026-08-25 |
| Single `/graph` route | Simple routing, consistent with existing routes | AI | 2026-08-25 |
| Static JSON only (no backend) | v1 scope, no dynamic generation needed | AI | 2026-08-25 |
| No new CI jobs | GOV-02 requirement, reuse existing pages job | AI | 2026-08-25 |

## Dependencies

- Phase 05: Unified Vite+FastAPI app must be in place (already complete)
- GitLab Pages: Existing Cytoscape.js implementation as reference

## Acceptance Tests

1. Navigate to `/graph` → see standards/crosswalks graph rendered
2. Click fullscreen button → graph expands to fullscreen mode
3. Check network tab → `crosswalk_graph.json` loaded from expected path
4. Navigate to `/` → navigation bar shows (Mappings, Graph, Stats, Convert)
5. Click `/stats` from graph page → stats page loads, graph state preserved
6. Push to main → `.gitlab-ci.yml` has exactly one `pages` job
