# The single command is `make dev` (DEP-039). `make lint` and `make test` are
# the binding gate that stands in for CI, which is a deliberate non-goal
# (CQ-079, 1-code-quality.md §13).

.PHONY: dev obs test lint build deploy clean venv help backend frontend

VENV := backend/.venv
BIN  := .venv/bin

help:           ## List the targets
	@grep -hE '^[a-z]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/\t/' | expand -t 12

venv:           ## Create the backend virtualenv and install the toolchain
	uv venv --python 3.12 $(VENV)
	cd backend && uv pip install -r requirements-dev.txt

dev:            ## Run the full stack locally with hot reload
	docker compose -f infra/docker-compose.yml up --build

obs:            ## Run the stack with the local LGTM observability stack
	docker compose -f infra/docker-compose.yml \
	               -f observability/docker-compose.observability.yml up --build

backend:        ## Run the backend alone, bare uvicorn with reload, against backend/data
	cd backend && DATA_DIR="$(CURDIR)/backend/data" ENVIRONMENT=development \
	  JWT_SECRET=dev-secret-not-for-production-0123456789abcdef \
	  $(BIN)/uvicorn app.main:app --port 8000 --reload

frontend:       ## Run the frontend alone, ng serve proxying /api to localhost:8000
	cd frontend && node scripts/generate-env.mjs && \
	  npx ng serve --port 4200 --proxy-config proxy.conf.local.json

test:
	cd backend && $(BIN)/pytest -q
	@if [ -f frontend/package.json ] && grep -q '"test"' frontend/package.json; then \
	  cd frontend && npm test -- --watch=false; \
	 fi
	@$(MAKE) e2e

# UI-068, UX-062: Playwright is a gate, not a convenience. It needs both a
# real backend and a real frontend running — a mocked one would prove nothing
# about UX-055/056/057/059/061, which are claims about the actual rendered
# page. DATA_DIR is a throwaway temp directory so this never touches
# backend/data; both servers are killed on exit whatever the test result.
e2e:
	@if [ ! -d frontend/e2e ]; then echo "frontend: e2e/ arrives with T26"; exit 0; fi
	@set -e; \
	 kill_stragglers() { \
	   pkill -f "uvicorn app\.main:app --port 8000" 2>/dev/null || true; \
	   pkill -f "ng serve --port 4200 --proxy-config proxy\.conf\.local\.json" 2>/dev/null || true; \
	 }; \
	 kill_stragglers; \
	 sleep 1; \
	 ( cd frontend && node scripts/generate-env.mjs ); \
	 tmp_data=$$(mktemp -d); \
	 cleanup() { kill $$uvicorn_pid $$ng_pid 2>/dev/null || true; kill_stragglers; rm -rf "$$tmp_data"; }; \
	 trap cleanup EXIT; \
	 ( cd backend && DATA_DIR="$$tmp_data" JWT_SECRET="e2e-test-secret-not-for-production-000" \
	   ENVIRONMENT=development $(BIN)/uvicorn app.main:app --port 8000 \
	   > /tmp/e2e-uvicorn.log 2>&1 ) & uvicorn_pid=$$!; \
	 ( cd frontend && npx ng serve --port 4200 --proxy-config proxy.conf.local.json \
	   > /tmp/e2e-ng-serve.log 2>&1 ) & ng_pid=$$!; \
	 for i in $$(seq 1 60); do curl -sf http://localhost:8000/health >/dev/null 2>&1 && break; sleep 1; done; \
	 for i in $$(seq 1 60); do curl -sf http://localhost:4200 >/dev/null 2>&1 && break; sleep 1; done; \
	 cd frontend && npx playwright test --project=chromium --project=chromium-375

lint:
	cd backend && $(BIN)/ruff check . && $(BIN)/mypy --strict app
# UI-027 and UI-063: a component stylesheet with content means the work is not
# done. UI-030 and UI-064: colours are tokens. Both are shell checks because no
# linter expresses them, and 3-ui.md Appendix B recorded them as missing.
# The hex check skips core/theme/: UI-039 mandates a PrimeNG preset written as
# hex literals, and that file is a declared token surface (ARC-037).
# Every stylesheet under src/ except styles.css, rather than "*.component.css":
# Angular 22 generates app.css for the root component, so the narrower glob
# matched nothing and the check passed while a stylesheet had content. See
# UI-027, corrected at T43.
	@! find frontend/src -name "*.css" ! -name "styles.css" -size +0c | grep -q . \
	  || { echo "UI-027: a component stylesheet is not empty"; exit 1; }
	@! grep -rEl "#[0-9a-fA-F]{3,8}\b" frontend/src \
	     --include='*.ts' --include='*.html' \
	     --exclude-dir=theme \
	  || { echo "UI-030/UI-064: hex colour outside a token surface"; exit 1; }
	@if [ -f frontend/eslint.config.js ]; then cd frontend && npm run lint; \
	 else echo "frontend: eslint config arrives with T26 (CQ-096)"; fi

build:
	docker build -f infra/Dockerfile -t borrower-portal .

deploy:
	fly deploy

clean:
	rm -f backend/data/app.db backend/data/app.db-wal backend/data/app.db-shm
	rm -rf backend/data/blobs
