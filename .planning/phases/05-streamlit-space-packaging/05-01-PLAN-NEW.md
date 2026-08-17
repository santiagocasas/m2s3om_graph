---
phase: 05-unified-vite-fastapi-packaging
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - server/main.py
  - server/requirements.txt
  - server/Dockerfile
  - web/src/convert.js
  - web/src/main.js
  - web/index.html
autonomous: false
requirements:
  - SPACE-01
  - SPACE-02
estimate:
  tokens: 40000
  raw_tokens: 20000
  tasks: 3
  confidence: medium
must_haves:
  truths:
    - "server/ exists with FastAPI app providing /health, /suggest, /convert"
    - "web/src/convert.js implements Convert a record page"
    - "Multi-stage Dockerfile builds Vite and serves via FastAPI"
  artifacts:
    - server/main.py
    - server/Dockerfile
    - Dockerfile
  key_links:
    - "server/main.py imports from m2s3om_graph.transform"
    - "web/src/main.js integrates Convert page"
---
<objective>
Promote suggestion API to server/, add /convert endpoint, extend Vite with Convert page, create unified multi-stage Dockerfile for Hugging Face Spaces.
</objective>
