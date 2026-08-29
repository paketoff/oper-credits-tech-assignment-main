---
id: DEP
title: Deployment & Observability
status: draft
version: 1.0.0
owner: paketoff
updated: 2026-08-29
---

# 5 — Deployment & Observability

Companion to [`2-architecture.md`](2-architecture.md), which says where files live. This document
covers containerisation, hosting, and the observability layer.

## 1. Decisions, and why

**DEP-001. One deployable artefact, not two.** Angular builds to static files; FastAPI serves them
from the same container. One machine, one process, no CORS, no reverse proxy, no second service to
keep in sync. In a two-hour budget, debugging a two-service deployment costs more than the
architectural purity is worth. This is a deliberate trade-off and belongs in the README.

**DEP-002. Fly.io, region `ams`.** It is on the brief's list of acceptable platforms, it gives EU
data residency in one line of config, and it supports a persistent volume without provisioning a
database.

**DEP-003. A volume for the database and the uploaded blobs.** The container filesystem is ephemeral:
without a volume, a restart destroys every user, application and document. A 1 GB volume mounted at
`/data` holds both the SQLite file and the uploaded files:

```
/data/app.db        SQLite database
/data/app.db-wal    write-ahead log
/data/app.db-shm    shared memory index
/data/blobs/        uploaded documents, keyed by application
```

**DEP-004.** The `-wal` and `-shm` files are part of the database in WAL mode
(`1-code-quality.md` CQ-084) and must live on the same volume as `app.db`. Splitting them, or putting
the database on the container filesystem and only the blobs on the volume, produces silent data loss
on restart.

This is what answers CQ-069: the ephemeral-filesystem caveat is not an accepted risk, it is closed by
the volume.

**DEP-005. Machines stay awake.** Fly stops idle machines by default and cold-starts them on request.
A reviewer opening the link and waiting several seconds reads as broken. `auto_stop_machines = false`
costs a few dollars a month and removes the risk.

**DEP-006. Observability config lives in `/observability`, instrumentation lives in the app.**
`app/core/telemetry.py` and `app/core/logging.py` are application code and stay in `app/`. Collector
and Grafana configuration are infrastructure and go in `/observability`. Splitting the code away from
the app would be worse, not tidier. → `2-architecture.md` ARC-041.

## 2. Repository layout

**DEP-007.** The tree is canonical in `2-architecture.md` ARC-002 and ARC-041. This spec owns what
goes *inside* each of these files:

```
infra/
  Dockerfile                        # multi-stage, production
  docker-compose.yml                # local development
  .dockerignore
  fly.toml
observability/
  otel-collector.yaml
  docker-compose.observability.yml
  grafana/
    datasources.yml
Makefile
.env.example
```

## 3. Dockerfile

**DEP-008.** Three stages. Dependencies install in their own layer so a code change does not
invalidate the cache.

```dockerfile
# ---------- 1. build the Angular bundle ----------
FROM node:22-alpine AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci
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

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

**DEP-053. `poppler-utils` is a runtime dependency, not a convenience.** `pdf2image`
(`9-ai-classification.md` AI-008) is a thin wrapper that shells out to `pdftoppm`; the package is
not in `python:3.12-slim`, and `pip install pdf2image` does not bring it. Without this line
classification works on a developer machine with Homebrew poppler and fails in the container — at
T37, in the last phase, which is the worst place to find it.

**DEP-009. `--host 0.0.0.0` is not optional.** Binding to `127.0.0.1` produces a container that works
locally and returns nothing on Fly. It is the most common first-deploy failure and it costs half an
hour to diagnose.

**DEP-010.** Check the Angular output path against `angular.json` before building. Angular 17+ emits
to `dist/<project>/browser`; an older layout omits the `browser` directory.

### 3.1 `.dockerignore`

**DEP-011.**

```
**/node_modules
**/__pycache__
**/.venv
**/dist
**/.angular
.git
.github
backend/data/
*.md
.env
```

**DEP-012.** Without this, the build context includes `node_modules` and the build slows to a crawl.

### 3.2 Python dependencies

**DEP-052.** Two manifests. `backend/requirements.txt` is runtime and is the only one the image
installs; `backend/requirements-dev.txt` carries the toolchain and never ships.

| `requirements.txt` | For |
|---|---|
| `fastapi`, `uvicorn[standard]` | the service (DEP-008) |
| `pydantic`, `pydantic-settings` | boundaries and config (CQ-024) |
| `sqlalchemy[asyncio]`, `aiosqlite`, `greenlet` | persistence (CQ-080) |
| `argon2-cffi` | passwords (AUTH-006) |
| `pyjwt` | the session token (AUTH-013) |
| `python-multipart` | document upload (API-048) |
| `structlog` | logging (DEP-029) |
| `opentelemetry-sdk`, `opentelemetry-instrumentation-fastapi`, `opentelemetry-exporter-otlp` | tracing (DEP-032) |
| `anthropic`, `pdf2image`, `pillow` | the optional classifier (AI-013, AI-008) |

`requirements-dev.txt`: `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`, `ruff`, `mypy`.

Three of these are easy to omit and fail in ways that do not name themselves. **`python-multipart`**
is not a FastAPI dependency: without it every `multipart/form-data` request is rejected before a
handler runs, so document upload returns an error that says nothing about a missing package.
**`greenlet`** is what SQLAlchemy's async layer bridges through; without it the first query raises a
`MissingGreenlet` far from the cause. **`pdf2image` additionally needs the system package** in
DEP-053.

## 4. Serving the SPA from FastAPI

**DEP-013.** Mount order matters, and the catch-all matters more.

```python
app.include_router(api_router, prefix="/api")
app.mount("/assets", StaticFiles(directory="static/assets"), name="assets")


@app.get("/health", response_model=LivenessResponse)
async def health(probe: HealthService = Depends(get_health_service)) -> LivenessResponse:
    """Liveness probe. Touches nothing."""
    return probe.liveness()


@app.get("/ready", response_model=ReadinessResponse)
async def ready(probe: HealthService = Depends(get_health_service)) -> ReadinessResponse:
    """Readiness probe: database reachable and the blob directory writable."""
    return await probe.readiness()


@app.get("/{path:path}")
async def spa(path: str) -> FileResponse:
    """Serve the Angular shell for any non-API route.

    Angular owns client-side routing, so a direct hit or a refresh on a deep
    route must return index.html rather than a 404.
    """
    return FileResponse("static/index.html")
```

**DEP-014.** Without the catch-all, refreshing on `/application/123` returns 404. That is exactly the
kind of edge case the reviewer will try.

**DEP-015. The controller rule applies to infrastructure endpoints too** (`1-code-quality.md` CQ-017,
CQ-018). The probes are one statement each; `SELECT 1` and the blob-directory check live in
`core/health.py`, not in a route handler, so `CQ-093` holds as well. The controller rule has no
exceptions and does not acquire its first one here.

## 5. Local development

**DEP-016.** Two services with hot reload. Production runs one container; development runs two,
because reloading Angular through a production build is unusable.

```yaml
# infra/docker-compose.yml
services:
  api:
    build:
      context: ..
      dockerfile: infra/Dockerfile
      target: deps
    working_dir: /app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ../backend:/app
      - ../backend/data:/data
    environment:
      DATA_DIR: /data
      JWT_SECRET: ${JWT_SECRET:-dev-secret-not-for-production}
      OTEL_EXPORTER_OTLP_ENDPOINT: ${OTEL_EXPORTER_OTLP_ENDPOINT:-}
    ports:
      - "8000:8000"

  web:
    image: node:22-alpine
    working_dir: /app
    command: sh -c "npm ci && npm start -- --host 0.0.0.0 --proxy-config proxy.conf.json"
    volumes:
      - ../frontend:/app
    ports:
      - "4200:4200"
    depends_on:
      - api
```

**DEP-051.** `DATABASE_URL` is **not** an environment variable. `core/config.py` derives it from
`DATA_DIR` as `sqlite+aiosqlite:///${DATA_DIR}/app.db` (`1-code-quality.md` CQ-081). Setting both
would give one path two sources: change `DATA_DIR` and the database quietly stays where it was.

**DEP-017.** `frontend/proxy.conf.json` forwards `/api` to `http://api:8000`, so the frontend calls
relative paths in development exactly as it does in production.

**DEP-018.** Secrets come from `.env`. The repository contains `.env.example` and never `.env`.

## 6. Fly configuration

**DEP-019.**

```toml
app = "oper-borrower-portal"
primary_region = "ams"

[build]
  dockerfile = "infra/Dockerfile"

[env]
  DATA_DIR = "/data"
  ENVIRONMENT = "production"

[[mounts]]
  source = "data"
  destination = "/data"

[http_service]
  internal_port = 8080
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

  [http_service.checks]
    [[http_service.checks.http]]
      path = "/health"
      interval = "30s"
      timeout = "3s"

[[vm]]
  size = "shared-cpu-1x"
  memory = "512mb"
```

**DEP-020.** `app` must be globally unique. If the name is taken, `fly launch` will ask for another.

### 6.1 First deploy

**DEP-021.**

```bash
curl -L https://fly.io/install.sh | sh
fly auth login

fly launch --no-deploy          # creates the app, asks for name and region
fly volumes create data --region ams --size 1
fly secrets set JWT_SECRET=$(openssl rand -hex 32)
fly secrets set ANTHROPIC_API_KEY=sk-ant-...
fly deploy
```

**DEP-022.** `--no-deploy` matters: it stops Fly deploying before the volume exists and before
`fly.toml` is edited.

**DEP-023.** Secrets are set through `fly secrets`, never committed. They land in the machine's
environment. A secret in `fly.toml` is a finding in any fintech review.

**DEP-024. `ANTHROPIC_API_KEY` has a consumer: the optional document classifier**,
[`9-ai-classification.md`](9-ai-classification.md). This was an open question for two rounds — the key
was set with nothing reading it — and it is now closed.

The classifier is behind `AI_CLASSIFICATION_ENABLED`, default off (AI-004), so both variables belong
in `.env.example`. With the flag off no client is constructed and the key is never read (AI-024),
which is what lets the key be revoked after the interview without the deployed app degrading.

### 6.2 When it does not work

**DEP-025.**

| Symptom | Cause |
|---|---|
| Deploy succeeds, URL returns nothing | Bound to `127.0.0.1` instead of `0.0.0.0` |
| 404 on every route except `/` | SPA catch-all missing |
| Data gone after redeploy | Volume not mounted, or `DATA_DIR` pointing outside `/data` |
| `database is locked` under load | WAL mode not enabled, or a session held open across an await |
| Slow first request | `auto_stop_machines` still true |
| Health check failing | `internal_port` does not match the port uvicorn binds |

**DEP-026.** `fly logs` streams output. `fly ssh console` opens a shell inside the machine.

### 6.3 Teardown after the interview

**DEP-027.**

```bash
fly apps destroy oper-borrower-portal
fly volumes list && fly volumes destroy <id>
```

**DEP-028. Volumes bill even when the machine is stopped.** Destroying the app alone leaves the
volume behind.

## 7. Observability

The brief names observability hooks as a scoring dimension. This layer is small, real, and
demonstrable in under twenty minutes.

### 7.1 Structured logging

- **DEP-029** — `structlog`, JSON to stdout. Fly collects stdout, so no log shipping is needed in
  production.
- **DEP-030** — Every log line carries `request_id`, injected by middleware and returned in an
  `X-Request-ID` response header, so a reported problem can be traced to its request.
- **DEP-031. Redaction is by default, not by exception.** A denylist covers `password`, `token`,
  `secret`, `api_key`, `authorization`, `email`, `full_name`, `filename`, and any key containing
  `amount`, `income` or `value`. Anything not explicitly allowed is not logged.

### 7.2 Tracing

**DEP-032.** OpenTelemetry with FastAPI auto-instrumentation, plus manual spans on the operations
that matter — two here, and a third, `document.classify`, when the optional classifier is enabled
(`9-ai-classification.md` AI-030):

- `simulation.compute` — attributes: `region`, `term_months`, `is_first_home`, `above_norm`. Never
  the amounts.
- `document.upload` — attributes: `doc_type`, `content_type`, `size_bucket` (a bucket, not the exact
  size). Never the filename.

**DEP-033.** Production exports to console; the collector endpoint is read from
`OTEL_EXPORTER_OTLP_ENDPOINT` and stays unset there. Locally, the LGTM stack is available through an
optional compose override so it does not consume memory on every start.

### 7.3 Metrics

**DEP-034.** Three, and no more. Metrics nobody reads are noise.

- `simulation_duration_seconds` — histogram. The calculator is the CPU-bound path (CQ-047).
- `documents_uploaded_total` — counter, labelled by `doc_type`.
- `application_transitions_total` — counter, labelled by `from_state` and `to_state`. This is the
  first-time-right loop made visible: repeated `DOCUMENTS_COMPLETE → DOCUMENTS_PENDING` transitions
  are exactly the failure mode the product exists to fix. → APP-004, APP-008.

### 7.4 Privacy rule

**DEP-035. No monetary amount, income figure, email address, name or original filename ever enters a
log line, a span attribute or a metric label.** Only identifiers, categories and buckets.

This is not decoration. In mortgage origination the payload is the sensitive data, and telemetry is
where it leaks. Saying this out loud in the README costs one sentence and reads correctly to anyone
from the domain. → DOM-020, DOC-003.

### 7.5 Endpoints

- **DEP-036** — `/health` — liveness only, no dependencies. It must not touch the database: a
  liveness probe that fails when the database is busy causes the platform to restart a healthy
  machine.
- **DEP-037** — `/ready` — readiness. Runs `SELECT 1` against the database and checks that
  `DATA_DIR/blobs` is writable. Returns 503 if either fails. The two checks cover the two stores kept
  deliberately separate in ARC-010: `core.database` and `core.storage`.

## 8. Makefile

**DEP-038.** The brief asks for one command if possible.

```make
.PHONY: dev test lint build deploy obs clean

dev:            ## Run the full stack locally with hot reload
	docker compose -f infra/docker-compose.yml up --build

obs:            ## Run the stack with the local LGTM observability stack
	docker compose -f infra/docker-compose.yml \
	               -f observability/docker-compose.observability.yml up --build

test:
	cd backend && pytest -q

lint:
	cd backend && ruff check . && mypy --strict app
	cd frontend && npm run lint
	@! find frontend/src -name "*.component.css" -size +0c | grep -q . \
	  || { echo "UI-027: a component stylesheet is not empty"; exit 1; }
	@! grep -rEl "#[0-9a-fA-F]{3,8}\b" frontend/src \
	     --include=*.ts --include=*.html \
	     --exclude-dir=theme \
	  || { echo "UI-030/UI-064: hex colour outside a token surface"; exit 1; }

build:
	docker build -f infra/Dockerfile -t borrower-portal .

deploy:
	fly deploy

clean:
	rm -f backend/data/app.db backend/data/app.db-wal backend/data/app.db-shm
	rm -rf backend/data/blobs
```

**DEP-039.** `make dev` is the single command in the README.

## 9. Order of work

**DEP-040. Deploy an empty skeleton first, before any feature work.**

1. `main.py` with `/health` and nothing else.
2. `Dockerfile`, `.dockerignore`, `fly.toml`.
3. `fly launch --no-deploy`, volume, secrets, `fly deploy`.
4. Confirm the public URL returns `{"status": "ok"}`.
5. Add `/ready` with the database check as soon as `core/database.py` exists, and confirm it passes
   against the mounted volume. A database that works locally and cannot write on the volume is a
   failure worth finding in minute twenty, not in hour three.

**DEP-041.** Twenty minutes, at the start, with a clear head. After that every push goes into a
pipeline that is already known to work, and deployment stops being a risk. This is unit D of
ARC-028, and ARC-029 already says it starts immediately and in parallel.

**DEP-042.** The opposite order — leaving deployment to the last hour — is the standard way to
discover a port or build-path problem with no time left to fix it.

## 10. Definition of done

- **DEP-043** — The public URL loads the application. → SCP-019.
- **DEP-044** — A direct hit on a deep route works, and refreshing it does not 404.
- **DEP-045** — Data survives `fly apps restart`: a user created before the restart can still log in
  afterwards, and their uploaded documents are still listed.
- **DEP-046** — `app.db`, its WAL files and `blobs/` all live under the mounted volume.
- **DEP-047** — No secret appears in the repository; `.env.example` documents every required
  variable.
- **DEP-048** — `make dev` brings the whole stack up locally.
- **DEP-049** — Every log line carries a `request_id`, and no log line contains an amount, an email
  or a filename.
- **DEP-050** — `/health` and `/ready` both respond.

---

# Appendix A — Traceability

Source: `07-deployment.md`, superseded by this document.

| ID | Statement | Source § | § |
|---|---|---|---|
| DEP-001 | One deployable artefact, not two | Decisions | §1 |
| DEP-002 | Fly.io, region `ams` | Decisions | §1 |
| DEP-003 | A 1 GB volume at `/data` for database and blobs | Decisions | §1 |
| DEP-004 | WAL and SHM live on the same volume as `app.db` | Decisions | §1 |
| DEP-005 | Machines stay awake, `auto_stop_machines = false` | Decisions | §1 |
| DEP-006 | Config in `/observability`, instrumentation in `app/` | Decisions | §1 |
| DEP-007 | The `infra/` and `observability/` file inventory | Repository layout | §2 |
| DEP-008 | Three-stage Dockerfile | 1 Dockerfile | §3 |
| DEP-009 | `--host 0.0.0.0` is not optional | 1 Dockerfile | §3 |
| DEP-010 | Check the Angular output path against `angular.json` | 1 Dockerfile | §3 |
| DEP-011 | `.dockerignore` contents | 1 `.dockerignore` | §3.1 |
| DEP-012 | Without it the build context includes `node_modules` | 1 `.dockerignore` | §3.1 |
| DEP-013 | Mount order and the route definitions | 2 Serving the SPA | §4 |
| DEP-014 | Without the catch-all, a deep refresh 404s | 2 Serving the SPA | §4 |
| DEP-015 | The controller rule applies to the probes too | added — resolves CQ-017 conflict | §4 |
| DEP-016 | Two services with hot reload in development | 3 Local development | §5 |
| DEP-017 | `proxy.conf.json` forwards `/api` | 3 Local development | §5 |
| DEP-018 | `.env.example` is committed, `.env` never | 3 Local development | §5 |
| DEP-019 | `fly.toml` | 4 Fly configuration | §6 |
| DEP-020 | `app` must be globally unique | 4 Fly configuration | §6 |
| DEP-021 | The first-deploy sequence | 4 First deploy | §6.1 |
| DEP-022 | `--no-deploy` before the volume exists | 4 First deploy | §6.1 |
| DEP-023 | Secrets via `fly secrets`, never in `fly.toml` | 4 First deploy | §6.1 |
| DEP-024 | `ANTHROPIC_API_KEY`'s consumer is the optional classifier | added — closed by `9-ai-classification.md` | §6.1 |
| DEP-025 | The six-row failure table | 4 When it does not work | §6.2 |
| DEP-026 | `fly logs`, `fly ssh console` | 4 When it does not work | §6.2 |
| DEP-027 | Teardown commands | 4 Teardown | §6.3 |
| DEP-028 | Volumes bill even when the machine is stopped | 4 Teardown | §6.3 |
| DEP-029 | `structlog`, JSON to stdout | 5 Structured logging | §7.1 |
| DEP-030 | `request_id` on every line, `X-Request-ID` header | 5 Structured logging | §7.1 |
| DEP-031 | Redaction by default; the nine-key denylist | 5 Structured logging | §7.1 |
| DEP-032 | Two manual spans and their attributes | 5 Tracing | §7.2 |
| DEP-033 | Console exporter in production; LGTM local and optional | 5 Tracing | §7.2 |
| DEP-034 | Three metrics, and no more | 5 Metrics | §7.3 |
| DEP-035 | The privacy rule | 5 Privacy rule | §7.4 |
| DEP-036 | `/health` is liveness only and touches nothing | 5 Endpoints | §7.5 |
| DEP-037 | `/ready` checks the database and the blob directory | 5 Endpoints | §7.5 |
| DEP-038 | The Makefile | 6 Makefile | §8 |
| DEP-039 | `make dev` is the single README command | 6 Makefile | §8 |
| DEP-040 | Deploy an empty skeleton first | 7 Order of work | §9 |
| DEP-041 | Twenty minutes at the start; this is unit D | 7 Order of work | §9 |
| DEP-042 | Leaving deployment to the last hour is the standard failure | 7 Order of work | §9 |
| DEP-043 | Done: the public URL loads the application | 8 Definition of done | §10 |
| DEP-044 | Done: a deep route works and survives refresh | 8 Definition of done | §10 |
| DEP-045 | Done: data survives `fly apps restart` | 8 Definition of done | §10 |
| DEP-046 | Done: database, WAL and blobs all on the volume | 8 Definition of done | §10 |
| DEP-047 | Done: no secret in the repository | 8 Definition of done | §10 |
| DEP-048 | Done: `make dev` brings the stack up | 8 Definition of done | §10 |
| DEP-049 | Done: `request_id` everywhere, no payload in logs | 8 Definition of done | §10 |
| DEP-050 | Done: `/health` and `/ready` both respond | 8 Definition of done | §10 |
| DEP-051 | `DATABASE_URL` is derived from `DATA_DIR`, never set twice | added in review | §5 |
| DEP-052 | The two dependency manifests, and the three easy omissions | added — nothing named the packages | §3.2 |
| DEP-053 | `poppler-utils` in the runtime stage for `pdf2image` | added — `pip install pdf2image` is not enough | §3 |

# Appendix B — Corrections against the source

Three values were changed while transcribing, because the source contradicted specs already approved.

| Source | Here | Why |
|---|---|---|
| `../data:/data`, `rm -f data/app.db`, `.dockerignore` `data/` | `backend/data` throughout | `ARC-002` places `data/` inside the backend tree and `.gitignore` already encodes `backend/data/*`. The container path stays `/data`. |
| `/health` returning a dict literal; `/ready` running `SELECT 1` in the handler | both delegate to `core/health.py` | `CQ-017` and `CQ-018` admit no exception, and inline SQL would also break `CQ-093` |
| — | DEP-024 added | The source sets `ANTHROPIC_API_KEY` with no consumer anywhere in the specs |
