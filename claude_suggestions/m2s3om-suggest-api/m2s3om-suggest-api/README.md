---
title: M2S3OM Suggest API
emoji: 🔗
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
---

# M²S³OM-graph Suggestion API

Thin FastAPI proxy that takes an uncovered field from a crosswalk and asks
Blablador for candidate mapping rules. Exists only so the Blablador API key
never has to live in client-side JavaScript on the static site.

## Setup

In this Space's Settings → Variables and secrets, set:

- `BLABLADOR_API_KEY` (secret)
- `BLABLADOR_BASE_URL` (variable, optional, defaults to the Helmholtz endpoint already in `main.py`)
- `M2S3OM_LLM_MODEL` (variable, optional, defaults to `alias-fast`)
- `SUGGEST_API_ALLOWED_ORIGINS` (variable, optional, comma-separated; defaults to `http://localhost:5173`)

## Endpoints

- `GET /health`
- `POST /suggest` — see `main.py` for the exact request/response schema, and `/docs` once deployed for interactive Swagger.

## Before deploying for real

1. Configure `SUGGEST_API_ALLOWED_ORIGINS` for the deployed environment if the static frontend is not served from `http://localhost:5173`.
2. ~~Replace `call_blablador()` with the existing Blablador client already used in the main pipeline repo, this stub duplicates a plain HTTP call and should not become a second thing to maintain.~~
3. Confirm `BLABLADOR_BASE_URL` matches the real Blablador endpoint your existing pipeline uses, the value here is a placeholder.

## Note on cold starts

Free-tier Spaces sleep after inactivity. The first request after idle time
has a delay of a few seconds while the container wakes up.
