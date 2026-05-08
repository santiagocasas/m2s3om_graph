#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if ! command -v uv >/dev/null 2>&1; then
    echo "uv is required but not installed." >&2
    exit 1
fi

"${ROOT_DIR}/scripts/run_surrealdb_local.sh" >/dev/null

M2S3OM_USE_SURREAL="${M2S3OM_USE_SURREAL:-1}"
M2S3OM_DB_URL="${M2S3OM_DB_URL:-ws://localhost:8000/rpc}"
M2S3OM_DB_NS="${M2S3OM_DB_NS:-m2s3om_graph}"
M2S3OM_DB_NAME="${M2S3OM_DB_NAME:-crosswalk}"
M2S3OM_DB_USER="${M2S3OM_DB_USER:-root}"
M2S3OM_DB_PASSWORD="${M2S3OM_DB_PASSWORD:-root}"
M2S3OM_BOOTSTRAP_RDAMSC="${M2S3OM_BOOTSTRAP_RDAMSC:-0}"
M2S3OM_SYNC_RDAMSC_CATALOG="${M2S3OM_SYNC_RDAMSC_CATALOG:-0}"
M2S3OM_DB_WAIT_ATTEMPTS="${M2S3OM_DB_WAIT_ATTEMPTS:-45}"
M2S3OM_DB_WAIT_DELAY="${M2S3OM_DB_WAIT_DELAY:-1}"
BOOTSTRAP_LOG_FILE="${ROOT_DIR}/.local/bootstrap_rdamsc.log"

mkdir -p "${ROOT_DIR}/.local"

if [[ "${M2S3OM_USE_SURREAL}" == "1" ]]; then
    echo "Waiting for SurrealDB readiness..."
    if ! uv run python "${ROOT_DIR}/scripts/helpers/wait_surreal_ready.py" \
        --url "${M2S3OM_DB_URL}" \
        --user "${M2S3OM_DB_USER}" \
        --password "${M2S3OM_DB_PASSWORD}" \
        --namespace "${M2S3OM_DB_NS}" \
        --database "${M2S3OM_DB_NAME}" \
        --attempts "${M2S3OM_DB_WAIT_ATTEMPTS}" \
        --delay "${M2S3OM_DB_WAIT_DELAY}"; then
        echo "SurrealDB is not ready after waiting. Aborting startup." >&2
        echo "Try: ./scripts/stop_surrealdb_local.sh && ./scripts/run_surrealdb_local.sh" >&2
        exit 1
    fi
fi

if [[ "${M2S3OM_SYNC_RDAMSC_CATALOG}" == "1" ]]; then
    echo "Running quick RDAMSC catalog sync..."
    if ! env \
        PYTHONUNBUFFERED=1 \
        M2S3OM_USE_SURREAL="${M2S3OM_USE_SURREAL}" \
        M2S3OM_DB_URL="${M2S3OM_DB_URL}" \
        M2S3OM_DB_NS="${M2S3OM_DB_NS}" \
        M2S3OM_DB_NAME="${M2S3OM_DB_NAME}" \
        M2S3OM_DB_USER="${M2S3OM_DB_USER}" \
        M2S3OM_DB_PASSWORD="${M2S3OM_DB_PASSWORD}" \
        uv run python -m m2s3om_graph.cli.main sync-rdamsc >/dev/null; then
        echo "Warning: quick catalog sync failed. Starting app anyway." >&2
    fi
fi

if [[ "${M2S3OM_BOOTSTRAP_RDAMSC}" == "1" ]]; then
    echo "Running verbose RDAMSC bootstrap pipeline..."
    echo "Log file: ${BOOTSTRAP_LOG_FILE}"
    if ! env \
        PYTHONUNBUFFERED=1 \
        M2S3OM_USE_SURREAL="${M2S3OM_USE_SURREAL}" \
        M2S3OM_DB_URL="${M2S3OM_DB_URL}" \
        M2S3OM_DB_NS="${M2S3OM_DB_NS}" \
        M2S3OM_DB_NAME="${M2S3OM_DB_NAME}" \
        M2S3OM_DB_USER="${M2S3OM_DB_USER}" \
        M2S3OM_DB_PASSWORD="${M2S3OM_DB_PASSWORD}" \
        uv run python -m m2s3om_graph.cli.main bootstrap-rdamsc --verbose --sssom-dir "${ROOT_DIR}/exports/sssom" | tee "${BOOTSTRAP_LOG_FILE}"; then
        echo "Warning: bootstrap step failed. Starting app anyway." >&2
    fi
else
    echo "Skipping heavy bootstrap (fast startup mode)."
    echo "Tip: set M2S3OM_BOOTSTRAP_RDAMSC=1 to run full startup ingestion."
fi

echo "Starting Streamlit with local SurrealDB defaults..."
echo "DB URL: ${M2S3OM_DB_URL}"

exec env \
    M2S3OM_USE_SURREAL="${M2S3OM_USE_SURREAL}" \
    M2S3OM_DB_URL="${M2S3OM_DB_URL}" \
    M2S3OM_DB_NS="${M2S3OM_DB_NS}" \
    M2S3OM_DB_NAME="${M2S3OM_DB_NAME}" \
    M2S3OM_DB_USER="${M2S3OM_DB_USER}" \
    M2S3OM_DB_PASSWORD="${M2S3OM_DB_PASSWORD}" \
    uv run streamlit run "${ROOT_DIR}/app/app.py" "$@"
