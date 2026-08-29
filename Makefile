# The single command is `make dev` (DEP-039). `make lint` and `make test` are
# the binding gate that stands in for CI, which is a deliberate non-goal
# (CQ-079, 1-code-quality.md §13).

.PHONY: dev obs test lint build deploy clean venv help

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

test:
	cd backend && $(BIN)/pytest -q

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
