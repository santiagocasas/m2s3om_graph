#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${CONTAINER_NAME:-m2s3om_graph-surrealdb}"

if ! command -v docker >/dev/null 2>&1; then
    echo "Docker is required but not installed." >&2
    exit 1
fi

if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker stop "${CONTAINER_NAME}" >/dev/null
    echo "Stopped ${CONTAINER_NAME}"
else
    echo "Container ${CONTAINER_NAME} is not running"
fi
