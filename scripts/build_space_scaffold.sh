#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SPACE_DIR="${ROOT_DIR}/spaces/m2s3om-streamlit-space"

mkdir -p "${SPACE_DIR}"
find "${SPACE_DIR}" -mindepth 1 ! -name '.gitkeep' -exec rm -rf {} +

mkdir -p "${SPACE_DIR}/app" "${SPACE_DIR}/src" "${SPACE_DIR}/exports/sssom"

cp -R "${ROOT_DIR}/app/." "${SPACE_DIR}/app/"
cp -R "${ROOT_DIR}/src/m2s3om_graph/." "${SPACE_DIR}/src/m2s3om_graph/"
cp "${ROOT_DIR}/pyproject.toml" "${SPACE_DIR}/pyproject.toml"

find "${SPACE_DIR}" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "${SPACE_DIR}" -type f -name '*.pyc' -delete

if compgen -G "${ROOT_DIR}/exports/sssom/*" > /dev/null; then
    cp -R "${ROOT_DIR}/exports/sssom/." "${SPACE_DIR}/exports/sssom/"
else
    touch "${SPACE_DIR}/exports/sssom/.gitkeep"
fi

uv export --format requirements-txt --no-hashes --output-file "${SPACE_DIR}/requirements.txt"

cat > "${SPACE_DIR}/Dockerfile" <<'EOF'
FROM python:3.12-slim
RUN useradd -m -u 1000 user
WORKDIR /home/user/app
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir -r requirements.txt
COPY --chown=user . .
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH PYTHONPATH=/home/user/app/src
EXPOSE 7860
CMD ["streamlit", "run", "app/app.py", "--server.port=7860", "--server.address=0.0.0.0"]
EOF

cat > "${SPACE_DIR}/.dockerignore" <<'EOF'
__pycache__
*.pyc
.git
.pytest_cache
claude_suggestions/
.planning/
tests/
spaces/
EOF

cat > "${SPACE_DIR}/README.md" <<'EOF'
---
title: M2S3OM Crosswalk Workbench
emoji: 🕸️
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# M2S3OM Crosswalk Workbench

Fully documented in plan 05-02.
EOF
