# Deferred Items — Phase 04 Browser Curation Workflow

- Full suite verification (`uv run --with pytest pytest tests/ -x -q`) is blocked by `tests/test_suggest_api.py` importing `fastapi`, which is not installed in the current environment (`ModuleNotFoundError: No module named 'fastapi'`). This is outside the curation workflow changes and was left for a dependency/setup follow-up.
