# syntax=docker/dockerfile:1
# Multi-stage build for Vite frontend + FastAPI backend
FROM node:20-alpine AS frontend
WORKDIR /app/web
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim AS backend
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SUGGEST_API_ALLOWED_ORIGINS="*" \
    PYTHONPATH=/app/src

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && rm -rf /var/lib/apt/lists/*

# Copy project
COPY . /app
# Copy built frontend
COPY --from=frontend /app/web/dist /app/web/dist

# Install Python deps
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir fastapi uvicorn pydantic requests && \
    pip install --no-cache-dir -e .

# Export crosswalk graph for Vite explorer
RUN python scripts/export_crosswalk_json.py || true

# Expose port
EXPOSE 7860

# Serve via FastAPI with static files
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "7860"]
