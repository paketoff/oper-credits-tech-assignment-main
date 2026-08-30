# One deployable artefact, not two (DEP-001): Angular builds to static files and
# FastAPI serves them from the same container.
#
# Three stages. Dependencies install in their own layer so a code change does not
# invalidate the cache (DEP-008).

# ---------- 1. build the Angular bundle ----------
FROM node:22-alpine AS frontend
WORKDIR /build
# The PrimeUI Community licence key. Not a runtime secret — it ships inside
# main.js and is visible to every browser — but it is per-developer, so it stays
# out of git (.env, gitignored) and reaches a container build as a build arg:
#   fly deploy --build-arg PRIMENG_LICENSE_KEY=...
# Absent, the build still succeeds and the app shows PrimeUI's licence banner.
ARG PRIMENG_LICENSE_KEY=""
ENV PRIMENG_LICENSE_KEY=$PRIMENG_LICENSE_KEY
COPY frontend/package*.json ./
# --legacy-peer-deps: npm 10.9's arborist crashes resolving the vitest peer
# graph Angular 22 scaffolds with ("Cannot read properties of null (reading
# 'edgesOut')"). The flag skips the peer walk that crashes; it does not change
# which versions the lockfile pins.
RUN npm ci --legacy-peer-deps
COPY frontend/ ./
RUN npm run build -- --configuration production

# ---------- 2. python dependencies ----------
FROM python:3.12-slim AS deps
ENV POETRY_VERSION=2.1.3 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true
WORKDIR /install
RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"
# The lock file, not the constraint list: this is what makes the image
# reproducible (DEP-052). Copied before the source so a code change does not
# invalidate the dependency layer.
COPY backend/pyproject.toml backend/poetry.lock backend/poetry.toml ./
RUN poetry install --only main --no-root

# ---------- 3. runtime ----------
FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DATA_DIR=/data

# pdf2image shells out to pdftoppm and pip does not bring it (DEP-053).
RUN apt-get update \
 && apt-get install -y --no-install-recommends poppler-utils \
 && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 app
WORKDIR /app

# Copied to the path it was built at, deliberately. A venv's console scripts
# carry an absolute shebang, so relocating it to /opt/venv would leave every
# entry point pointing at a python that is not there.
COPY --from=deps /install/.venv /install/.venv
ENV PATH="/install/.venv/bin:$PATH"

COPY backend/app ./app
COPY --from=frontend /build/dist/borrower-portal/browser ./static

RUN mkdir -p /data && chown -R app:app /data /app
USER app

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/health').status==200 else 1)"

# --host 0.0.0.0 is not optional (DEP-009). Binding to 127.0.0.1 produces a
# container that works locally and returns nothing on Fly.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
