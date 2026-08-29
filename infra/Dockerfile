# One deployable artefact, not two (DEP-001): Angular builds to static files and
# FastAPI serves them from the same container.
#
# Three stages. Dependencies install in their own layer so a code change does not
# invalidate the cache (DEP-008).

# ---------- 1. build the Angular bundle ----------
FROM node:22-alpine AS frontend
WORKDIR /build
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
WORKDIR /install
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir --prefix=/install/deps -r requirements.txt

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

COPY --from=deps /install/deps /usr/local
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
