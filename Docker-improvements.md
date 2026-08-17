# Docker Improvements

## Current pain
First build is slow because Node deps, Python deps, Vite build, and source copy all happen from scratch.

## Caching strategy
Docker builds images as layers. A layer is reused if its inputs haven't changed.

### .dockerignore
Create `.dockerignore` to avoid invalidating caches with irrelevant files:
```
.git
.venv
__pycache__
*.pyc
.pytest_cache
.mypy_cache
.sisyphus
tests
docs
```

### Cache-friendly Dockerfile order
1. Copy dependency manifests first
2. Install dependencies
3. Copy source code last

For Python:
```dockerfile
COPY pyproject.toml uv.lock /app/
RUN pip install -U pip && pip install -e .
COPY . /app
```

For Node:
```dockerfile
COPY web/package*.json /app/web/
RUN npm ci
COPY web/ /app/web/
RUN npm run build
```

### Build cache reuse
- Local builds reuse Docker's local layer cache automatically.
- Push to registry for remote reuse:
  ```bash
  docker tag m2s3om-graph youruser/m2s3om-graph:latest
  docker push youruser/m2s3om-graph:latest
  ```
- Pull later: `docker pull youruser/m2s3om-graph:latest`

### Save/load tarball
```bash
docker save m2s3om-graph -o m2s3om-graph.tar
docker load -i m2s3om-graph.tar
```

### HF Spaces notes
HF Spaces builds on their runners. Keep dependency installs early and stable to maximize cache hits. Pin versions in package manifests.

### Optional BuildKit caches
For advanced caching of pip/npm caches:
```dockerfile
RUN --mount=type=cache,target=/root/.cache/pip pip install ...
```

## Next steps
- Add .dockerignore
- Refactor Dockerfile to copy pyproject.toml + uv.lock before source
- Pin Node/Python versions
- Consider multi-stage cache mounts for pip/npm
