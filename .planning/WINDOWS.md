---
schema_version: 1
open_count: 1
waived_count: 0
fixed_count: 0
total_count: 1
last_updated: 2026-08-16T11:38:40.445Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 04 | deviation | tests/test_suggest_api.py |  | Full-suite verification blocked by missing fastapi dependency in unrelated suggest API test | open |  | 2026-08-16T11:38:40.445Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "04",
    "file": "tests/test_suggest_api.py",
    "line": null,
    "description": "Full-suite verification blocked by missing fastapi dependency in unrelated suggest API test",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-16T11:38:40.445Z",
    "resolved_at": null
  }
]
````
