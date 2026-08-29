# oper-credits-tech-assignment

Monorepo built with a spec-driven workflow: behaviour is specified in
[`specs/`](specs/) first, then implemented.

## Stack

| Area | Choice |
|---|---|
| `backend/` | Python 3.12 + FastAPI |
| `frontend/` | Angular + TypeScript |
| `infra/` | Docker (tentative) |
| `observability/` | LGTM stack — Loki, Grafana, Tempo, Mimir (tentative) |

## Layout

```
backend/         API service
frontend/        Angular SPA
infra/           Containerisation, deployment, local orchestration
observability/   Logs, metrics, traces, dashboards
specs/           Specifications — source of truth
.claude/         Claude Code configuration (commands, agents, skills)
```

## Working agreement

1. Write or update the spec in `specs/`.
2. Implement against it, referencing requirement IDs (`BL-001`, ...).
3. Keep the spec and the code in sync — the spec is not documentation written
   after the fact.

The domain — scope, entities, lifecycle and the calculation engine — is specified in
[`specs/0-business-logic.md`](specs/0-business-logic.md). Spec conventions and ID namespaces
live in [`specs/README.md`](specs/README.md).
