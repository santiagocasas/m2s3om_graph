---
title: M2S3OM Pipeline Console
emoji: 🕸️
colorFrom: gray
colorTo: blue
sdk: docker
app_port: 7860
---

# M²S³OM-graph Pipeline & Convert Console

The full operator console: run the extraction pipeline on any RDAMSC
crosswalk, inspect live logs and status, and convert a real record
end-to-end. This is the heavier counterpart to the static Browse site,
linked from there rather than embedded in it.

## Setup

In this Space's Settings → Variables and secrets, set whatever this app
already needs locally, at minimum:

- `BLABLADOR_API_KEY` (secret)
- SurrealDB connection details (see note below)

## Note on SurrealDB

If the existing app currently connects to a SurrealDB instance running on
localhost, that won't exist once this is deployed as a Space. Options:

1. Point at a SurrealDB Cloud instance (or any reachable SurrealDB server) via environment variables instead of a hardcoded localhost URL.
2. Run an embedded SurrealKV file on the Space's own ephemeral disk (50 GB free, but resets on restart/pause, fine for a demo, not for permanent storage).

Either way, the connection target should come from an environment variable,
not be hardcoded, so the same code works unchanged locally and on the Space.

## Important: native Streamlit SDK is deprecated on Spaces

Hugging Face now recommends the Docker SDK with the standard Streamlit
template (which is what this Dockerfile is) rather than the old built-in
`sdk: streamlit` option. This Dockerfile follows that current guidance.

## What still needs to happen before this works

1. Copy the existing `app.py` (and any supporting modules/`requirements.txt`) into this folder, alongside this Dockerfile and README.
2. Replace hardcoded connection strings/paths with `os.environ.get(...)` reads.
3. Confirm the requirements file doesn't assume a local-only dependency (e.g. a SurrealDB binary path that only exists on the dev machine).

## Note on cold starts

Free-tier Spaces sleep after inactivity. The first request after idle time
has a delay while the container restarts.
