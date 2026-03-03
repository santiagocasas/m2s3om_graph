#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

DB_DIR="${DB_DIR:-${ROOT_DIR}/.local/surrealdb}"
PORT="${PORT:-8000}"
CONTAINER_NAME="${CONTAINER_NAME:-kaigraph-surrealdb}"
PORT_CHECK_SCRIPT="${ROOT_DIR}/scripts/helpers/is_port_open.py"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required but not installed." >&2
    exit 1
fi

is_port_open() {
    local port="$1"
    python3 "${PORT_CHECK_SCRIPT}" "127.0.0.1" "${port}"
}

wait_for_port() {
    local port="$1"
    local tries="${2:-30}"
    for _ in $(seq 1 "${tries}"); do
        if is_port_open "${port}"; then
            return 0
        fi
        sleep 1
    done
    return 1
}

mkdir -p "${DB_DIR}"

if is_port_open "${PORT}"; then
    if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        echo "SurrealDB is already running in container '${CONTAINER_NAME}'."
        echo "SurrealDB running at ws://localhost:${PORT}/rpc"
        exit 0
    fi
    echo "Port ${PORT} is already in use (and '${CONTAINER_NAME}' is not running)." >&2
    echo "Set PORT=... to use a different host port." >&2
    exit 1
fi

if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker start "${CONTAINER_NAME}" >/dev/null
else
    docker run -d --name "${CONTAINER_NAME}" -p "${PORT}:8000" \
        -u "$(id -u):$(id -g)" \
        -v "${DB_DIR}:/dbs/kaigraph" \
        surrealdb/surrealdb:latest \
        start --user root --pass root rocksdb:/dbs/kaigraph >/dev/null
fi

if ! wait_for_port "${PORT}" 30; then
    echo "SurrealDB did not start on port ${PORT}." >&2
    docker logs "${CONTAINER_NAME}" >&2
    exit 1
fi

echo "SurrealDB running at ws://localhost:${PORT}/rpc"
echo "Use env:"
echo "  export KAIGRAPH_USE_SURREAL=1"
echo "  export KAIGRAPH_DB_URL=ws://localhost:${PORT}/rpc"
echo "  export KAIGRAPH_DB_NS=kaigraph"
echo "  export KAIGRAPH_DB_NAME=crosswalk"
echo "  export KAIGRAPH_DB_USER=root"
echo "  export KAIGRAPH_DB_PASSWORD=root"
