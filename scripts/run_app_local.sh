#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required but not installed." >&2
    exit 1
fi

"${ROOT_DIR}/scripts/run_surrealdb_local.sh" >/dev/null

KAIGRAPH_USE_SURREAL="${KAIGRAPH_USE_SURREAL:-1}"
KAIGRAPH_DB_URL="${KAIGRAPH_DB_URL:-ws://localhost:8000/rpc}"
KAIGRAPH_DB_NS="${KAIGRAPH_DB_NS:-kaigraph}"
KAIGRAPH_DB_NAME="${KAIGRAPH_DB_NAME:-crosswalk}"
KAIGRAPH_DB_USER="${KAIGRAPH_DB_USER:-root}"
KAIGRAPH_DB_PASSWORD="${KAIGRAPH_DB_PASSWORD:-root}"
KAIGRAPH_BOOTSTRAP_RDAMSC="${KAIGRAPH_BOOTSTRAP_RDAMSC:-0}"
KAIGRAPH_SYNC_RDAMSC_CATALOG="${KAIGRAPH_SYNC_RDAMSC_CATALOG:-0}"
KAIGRAPH_DB_WAIT_ATTEMPTS="${KAIGRAPH_DB_WAIT_ATTEMPTS:-45}"
KAIGRAPH_DB_WAIT_DELAY="${KAIGRAPH_DB_WAIT_DELAY:-1}"
BOOTSTRAP_LOG_FILE="${ROOT_DIR}/.local/bootstrap_rdamsc.log"

mkdir -p "${ROOT_DIR}/.local"

if [[ "${KAIGRAPH_USE_SURREAL}" == "1" ]]; then
    echo "Waiting for SurrealDB readiness..."
    if ! uv run python "${ROOT_DIR}/scripts/helpers/wait_surreal_ready.py" \
        --url "${KAIGRAPH_DB_URL}" \
        --user "${KAIGRAPH_DB_USER}" \
        --password "${KAIGRAPH_DB_PASSWORD}" \
        --namespace "${KAIGRAPH_DB_NS}" \
        --database "${KAIGRAPH_DB_NAME}" \
        --attempts "${KAIGRAPH_DB_WAIT_ATTEMPTS}" \
        --delay "${KAIGRAPH_DB_WAIT_DELAY}"; then
        echo "SurrealDB is not ready after waiting. Aborting startup." >&2
        echo "Try: ./scripts/stop_surrealdb_local.sh && ./scripts/run_surrealdb_local.sh" >&2
        exit 1
    fi
fi

if [[ "${KAIGRAPH_SYNC_RDAMSC_CATALOG}" == "1" ]]; then
    echo "Running quick RDAMSC catalog sync..."
    if ! env \
        PYTHONUNBUFFERED=1 \
        KAIGRAPH_USE_SURREAL="${KAIGRAPH_USE_SURREAL}" \
        KAIGRAPH_DB_URL="${KAIGRAPH_DB_URL}" \
        KAIGRAPH_DB_NS="${KAIGRAPH_DB_NS}" \
        KAIGRAPH_DB_NAME="${KAIGRAPH_DB_NAME}" \
        KAIGRAPH_DB_USER="${KAIGRAPH_DB_USER}" \
        KAIGRAPH_DB_PASSWORD="${KAIGRAPH_DB_PASSWORD}" \
        uv run python -m kaigraph.cli.main sync-rdamsc >/dev/null; then
        echo "Warning: quick catalog sync failed. Starting app anyway." >&2
    fi
fi

if [[ "${KAIGRAPH_BOOTSTRAP_RDAMSC}" == "1" ]]; then
    echo "Running verbose RDAMSC bootstrap pipeline..."
    echo "Log file: ${BOOTSTRAP_LOG_FILE}"
    if ! env \
        PYTHONUNBUFFERED=1 \
        KAIGRAPH_USE_SURREAL="${KAIGRAPH_USE_SURREAL}" \
        KAIGRAPH_DB_URL="${KAIGRAPH_DB_URL}" \
        KAIGRAPH_DB_NS="${KAIGRAPH_DB_NS}" \
        KAIGRAPH_DB_NAME="${KAIGRAPH_DB_NAME}" \
        KAIGRAPH_DB_USER="${KAIGRAPH_DB_USER}" \
        KAIGRAPH_DB_PASSWORD="${KAIGRAPH_DB_PASSWORD}" \
        uv run python -m kaigraph.cli.main bootstrap-rdamsc --verbose --sssom-dir "${ROOT_DIR}/exports/sssom" | tee "${BOOTSTRAP_LOG_FILE}"; then
        echo "Warning: bootstrap step failed. Starting app anyway." >&2
    fi
else
    echo "Skipping heavy bootstrap (fast startup mode)."
    echo "Tip: set KAIGRAPH_BOOTSTRAP_RDAMSC=1 to run full startup ingestion."
fi

echo "Starting Streamlit with local SurrealDB defaults..."
echo "DB URL: ${KAIGRAPH_DB_URL}"

exec env \
    KAIGRAPH_USE_SURREAL="${KAIGRAPH_USE_SURREAL}" \
    KAIGRAPH_DB_URL="${KAIGRAPH_DB_URL}" \
    KAIGRAPH_DB_NS="${KAIGRAPH_DB_NS}" \
    KAIGRAPH_DB_NAME="${KAIGRAPH_DB_NAME}" \
    KAIGRAPH_DB_USER="${KAIGRAPH_DB_USER}" \
    KAIGRAPH_DB_PASSWORD="${KAIGRAPH_DB_PASSWORD}" \
    uv run streamlit run "${ROOT_DIR}/app/app.py" "$@"
