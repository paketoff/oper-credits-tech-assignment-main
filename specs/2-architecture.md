---
id: ARC
title: Architecture
status: draft
version: 1.0.0
owner: paketoff
updated: 2026-08-29
---

# 2 — Architecture

Companion to [`1-code-quality.md`](1-code-quality.md). That document says **how code is written**;
this one says **where it lives and what may import what**. Where the two overlap, this file is
canonical for structure, layering and import boundaries, and `1-code-quality.md` carries a one-line
statement pointing here.

Both are subordinate to [`0-business-logic.md`](0-business-logic.md): where a spec and the business
spec disagree, the business spec wins.

## 1. Principle

**ARC-001. Organise by domain, not by technical layer.**

The alternative — `routers/`, `services/`, `models/` — spreads one feature across four folders. Every
change touches four places and nothing tells you where a feature begins or ends. Grouping by domain
means a feature is a folder, its boundary is visible, and it can be deleted in one move.

## 2. Backend

**ARC-002.** The repository root:

```
backend/          FastAPI service, the tree below
  pyproject.toml  ruff + mypy configuration (CQ-096); the rule set does not apply without it
frontend/         Angular SPA
  eslint.config.js  the TypeScript rule set (CQ-096)
infra/            Dockerfile, compose, fly.toml, .dockerignore
observability/    collector and Grafana configuration
specs/            the specifications
docs/sessions/    agent session logs, by phase (10-implementation T05, T41)
.claude/          agent configuration
Makefile          make dev is the single command
.env.example      every required variable, no values
CLAUDE.md
README.md
```

**ARC-041.** `infra/` and `observability/` hold **configuration only**. Instrumentation —
`core/telemetry.py` and `core/logging.py` — is application code and stays in `app/`. Splitting the
code away from the app would be worse, not tidier. What goes inside each infra file is
[`5-deployment.md`](5-deployment.md) §2 – §8; this spec owns only where they sit.

The backend tree, rooted at `backend/`:

```
app/
  domains/
    simulation/
      __init__.py
      router.py            # HTTP routes; one service call per handler
      service.py           # orchestration, domain flow
      schemas.py           # pydantic request/response models
      calculator.py        # pure maths; no IO, no framework
      repository.py        # queries against this domain's tables
      tables.py            # SQLAlchemy table definitions
      entities.py          # internal domain model
    applications/
      router.py
      service.py
      schemas.py
      tables.py
      entities.py
      state_machine.py     # allowed transitions; pure
      checklist.py         # required_documents(application); pure
      repository.py
    documents/
      router.py
      service.py
      schemas.py
      tables.py
      entities.py
      file_type.py         # magic-byte detection; pure
      classification/      # optional feature, 9-ai-classification.md
        prompts.py         # the system prompt, a module-level constant
        evaluator.py        # the decision table; pure
        client.py          # the API call
      repository.py
    auth/
      router.py
      service.py
      dependencies.py      # current_user; a public surface, see ARC-042
      security.py          # argon2 hashing, token encode/decode
      schemas.py
      tables.py
      entities.py
      repository.py

  core/
    config.py              # pydantic-settings
    database.py            # engine, session factory, get_session, pragmas
    enums.py               # value enums shared by two domains; imports nothing (ARC-044)
    health.py              # liveness and readiness probes, behind a service
    limits.py              # request body size guard (VAL-024); imports no domain
    rate_limit.py          # generic per-IP limiter; imports no domain
    errors.py              # domain exception base + stable codes
    exception_handlers.py  # domain error -> HTTP, registered once
    logging.py             # structured logging
    telemetry.py           # OpenTelemetry hooks
    storage.py             # StorageBackend protocol + LocalStorage (blobs only)
    dependencies.py        # shared DI providers

  main.py                  # app factory, router registration, handler registration

tests/
  domains/
    simulation/
      test_calculator.py
      test_service.py
      test_api.py
    applications/
      test_state_machine.py
      test_checklist.py
      test_api.py
    documents/
      test_api.py
  conftest.py

data/                      # DATA_DIR: app.db + blobs/, gitignored except .gitkeep
static/                    # built Angular bundle, served by FastAPI
```

**ARC-003.** Every domain has the same internal shape, so an unfamiliar one needs no orientation.

## 3. What each file owns

| ID | File | Owns | Never contains |
|---|---|---|---|
| ARC-004 | `router.py` | Route declarations, status codes, dependency wiring | Logic, branching, repository calls |
| ARC-005 | `service.py` | The flow: validate, call pure functions, persist, assemble | Maths, storage details, HTTP concepts |
| ARC-006 | `schemas.py` | The wire contract in and out | Persistence models, business rules |
| ARC-007 | `entities.py` | Internal domain representation | Serialisation or persistence concerns |
| ARC-038 | `tables.py` | SQLAlchemy table definitions, columns, keys, indexes | Business rules, wire concerns, queries |
| ARC-008 | `calculator.py` `state_machine.py` `checklist.py` `file_type.py` `classification/evaluator.py` | Pure domain logic | Imports of FastAPI, repository, config |
| ARC-009 | `repository.py` | Queries against its own tables; the only place `select`/`insert`/`update`/`delete` appear | Business rules, transaction control |

`router.py` holding exactly one statement per handler is the controller rule, `1-code-quality.md`
CQ-017.

## 4. Dependency direction

**ARC-010.**

```
router  →  service  →  { calculator | state_machine | checklist }
                    →  repository  →  core.database   (rows)
                    →  repository  →  core.storage    (uploaded blobs)
                    ↘
                     core.errors
```

Arrows point one way only.

**`core.database` and `core.storage` are different things and must not be conflated.**
`core.database` owns the SQLite connection and the request session; `core.storage` owns the
`StorageBackend` protocol for uploaded file blobs, which live on the filesystem at `DATA_DIR/blobs`
and are **never** stored in the database. A `Document` row carries an opaque `storage_key`
(`0-business-logic.md` DOC-003); the bytes it points at are the blob.

**Rules:**

- **ARC-011** — A domain never imports another domain's internals. Cross-domain access goes through
  the other domain's **declared public surface**: `service.py`, and for `auth` also
  `dependencies.py` (ARC-042). Injected as a dependency.
- **ARC-012** — `core` never imports from `domains`.
- **ARC-013** — Pure modules (`calculator`, `state_machine`, `checklist`, `file_type`,
  `classification/evaluator`) import only the standard library, `decimal`, their own domain's
  `entities.py`, and the two `core` leaves — `core/enums.py` (ARC-044) and `core/errors.py`
  (ARC-045). `evaluate` in particular imports no API client and no session — that is what makes the
  classifier's decision table testable without a network (`9-ai-classification.md` AI-014). They
  never import SQLAlchemy, a session, or `tables.py`.
- **ARC-045** — `core/errors.py` is on that whitelist because the pure modules are where several
  registry codes are raised: `7-validation.md` VAL-004 names the calculator as the source of
  `JKP_COMPUTATION_FAILED` and the state machine as the source of `INVALID_STATE_TRANSITION`, and
  `1-code-quality.md` CQ-054 shows `compute_jkp` raising `SimulationError` directly. Without this the
  spec asks for something it also forbids. Like `enums.py`, the module is a leaf: exception classes
  and their codes, importing nothing but the standard library. **Purity here means no IO, no
  framework and no session — not the absence of a shared vocabulary.**
- **ARC-014** — `main.py` is the only file that knows about all domains.
- **ARC-042** — `domains/auth/dependencies.py` is the auth domain's second public surface, and the
  only such exception in the codebase. It exists because `current_user` is needed by every domain's
  router while resolving through `AuthService`: `core` may not import a domain (ARC-012), so it
  cannot live there. The exception is narrow — the dependency may read the request and delegate to
  `auth.service`, and nothing else. It never touches a repository. A named exception is cheaper than
  a protocol layer built for one consumer (`1-code-quality.md` CQ-001).
- **ARC-039** — `core/database.py` owns the connection and nothing else: the engine, the
  `async_sessionmaker`, the declarative base, the `get_session` dependency, and pragma setup on
  connect. It knows no table and imports no domain — ARC-012 applies to it like any other `core`
  module.
- **ARC-044** — `core/enums.py` holds the value enums that **two domains genuinely share**, and only
  those: `Region` (simulation prices the tax, applications stores the property) and `DocumentType`
  (applications derives the checklist from it, documents validates an upload against it). It is a
  leaf: it imports nothing, not even `decimal`, which is why ARC-013 can admit it without weakening
  the purity rule. The alternative is a second definition of `DocumentType` in each domain, and the
  first time one of them gains a member the checklist and the uploader disagree about what satisfies
  a requirement — the one thing `0-business-logic.md` DOC-008 cannot survive. Enums with a single
  domain stay in that domain's `entities.py`: `PropertyType`, `EmploymentType` and
  `ApplicationStatus` all belong to `applications/`.

**ARC-015.** Violating rule ARC-011 or ARC-012 is a design error, not a shortcut. If a feature seems
to require it, the boundary is drawn wrong.

## 5. Known cross-domain edges

**ARC-016.** Only two exist. Both are declared here so nobody has to invent a third.

- **ARC-017** — `auth.service` → `simulation.service.claim_for_user()` — attaches an anonymous
  simulation to a newly registered user. Implements `0-business-logic.md` DOM-025 – DOM-027.
- **ARC-018** — `documents.service` → `applications.service.recompute_status()` — an upload or
  deletion can move an application between `DOCUMENTS_PENDING` and `DOCUMENTS_COMPLETE`. Implements
  APP-003 and APP-004.

**ARC-019.** Both are one-directional service calls. Neither reaches into the other domain's
repository.

## 6. Frontend (Angular)

**ARC-020.** Mirrors the backend deliberately: the same four domains, the same layering. Moving
between the two halves costs nothing.

```
src/app/
  domains/
    simulation/
      simulation.service.ts       # HTTP + state for this domain
      simulation.models.ts        # mirrors backend schemas
      pages/
        simulator-page.component.ts
      components/
        simulation-form.component.ts
        simulation-result.component.ts
    application/
      application.service.ts
      application.models.ts
      pages/
        application-wizard.component.ts
      components/
        borrower-step.component.ts
        property-step.component.ts
        review-step.component.ts
    documents/
      documents.service.ts
      documents.models.ts
      components/
        checklist.component.ts
        upload-field.component.ts
    auth/
      auth.service.ts
      auth.models.ts
      auth.guard.ts
      pages/
        signup-page.component.ts
        login-page.component.ts

  core/
    theme/
      oper-preset.ts              # the entire PrimeNG visual language
    api.client.ts                 # base HTTP wrapper
    error.interceptor.ts          # maps backend error codes to messages
    auth.interceptor.ts
    error-codes.ts                # mirrors core/errors.py

  shared/
    money.pipe.ts
    percent.pipe.ts
    components/                   # dumb, reusable, no business logic

  app.routes.ts
  app.config.ts

src/styles.css                    # Tailwind v4 @theme; the only @apply site
```

**ARC-037.** `core/theme/oper-preset.ts` is the only place PrimeNG component appearance is defined,
and `src/styles.css` is the only place the design tokens live. Component styles are never overridden
with a CSS class and no `*.component.css` carries content — if something looks wrong, the token is
wrong. The design reasoning is `3-ui.md` §6.2; this is the structural half of it.

## 7. Frontend rules

- **ARC-021** — **A component never calls HTTP.** It calls its domain service. Same reasoning as the
  controller rule on the backend (CQ-017).
- **ARC-022** — **Pages hold state, components receive inputs.** A component under `components/`
  takes `@Input` and emits `@Output`; it does not inject a domain service. Only `pages/` do.
- **ARC-023** — **`shared/` has no business logic and no domain imports.** If something in `shared/`
  needs to know about mortgages, it belongs in a domain.
- **ARC-024** — A domain does not import another domain's components. Cross-domain goes through
  services.
- **ARC-025** — Standalone components throughout. No `NgModule`.
- **ARC-026** — **Money is `string` end to end.** Parse only for display; never round-trip through
  `number`. Full rule and rationale: `1-code-quality.md` CQ-014, CQ-027.

## 8. Model mirroring

**ARC-027.** `simulation.models.ts` mirrors `schemas.py` **field for field** — same field names, same
casing as the wire format. Type names are per-layer and need not match (`SimulationResponse` in
pydantic is `Simulation` in TypeScript); it is the field names that must never drift. No renaming layer. If a field is `total_cash_needed` on the wire, it is
`total_cash_needed` in TypeScript. Renaming buys nothing and costs a mapping function that will
drift.

## 9. Ownership boundaries for parallel work

**ARC-028.** The folder structure is also the concurrency plan. Four units of work, no shared files.

| Unit | Owns | Depends on |
|---|---|---|
| A — domain core | `domains/simulation/{calculator,entities}.py`, `domains/applications/{state_machine,checklist,entities}.py`, `domains/documents/{file_type,classification/evaluator}.py`, their tests | nothing |
| B — API surface | all `router.py`, `service.py`, `schemas.py`, `tables.py`, `repository.py`, and `documents/classification/{client,prompts}.py` | A's entities and function signatures, D's `core/database.py` |
| C — frontend | everything under `src/app/` | B's wire contract |
| D — platform | `core/*` — **including `core/database.py`, `core/storage.py`, `core/health.py` and `core/rate_limit.py`** — `main.py`, `infra/*`, `observability/*`, `Makefile`, `.env.example` | nothing |

**ARC-029.** A and D can start immediately and in parallel. B starts once A's signatures exist and
D's `get_session` dependency exists. C starts once B's schemas exist — the contract, not the
implementation, is the unblocker.

**ARC-030.** Nobody edits `main.py` except D. Nobody edits a pure module except A.

## 10. A request, end to end

**ARC-031.** `POST /api/simulations` with a body:

1. `simulation/router.py` — FastAPI validates the body into `SimulationRequest`, injects
   `SimulationService`, makes one call.
2. `simulation/service.py` — calls `calculator.simulate()`, builds a `Simulation` model, persists it
   via `repository.save()`, returns a `SimulationResponse`.
3. `simulation/calculator.py` — pure: monthly rate, annuity, schedule, upfront costs, JKP.
4. `simulation/repository.py` — inserts one row using the request session from `core.database`.
   The service, not the repository, commits the transaction (`1-code-quality.md` CQ-091).
5. On a domain error anywhere: raised as a `DomainError` subclass, caught once in
   `core/exception_handlers.py`, rendered as `{"code": ..., "message": ...}` with the right status.

The route handler stays one line. Every layer below it is testable without HTTP.

## 11. Naming

- **ARC-032** — Python modules: `snake_case`, singular for a concept (`calculator.py`), plural for a
  collection domain (`documents/`).
- **ARC-033** — Domain folders take the plural of the aggregate: `applications/`, `documents/`.
  `simulation/` and `auth/` stay singular because they name a capability, not a collection.
- **ARC-034** — Angular files: `<name>.<role>.ts` — `simulation.service.ts`,
  `checklist.component.ts`.
- **ARC-035** — Test files mirror the module under test: `calculator.py` → `test_calculator.py`.
- **ARC-043** — The simulation domain makes the three-file split concrete, and the names are not
  interchangeable:

  | Type | Lives in | Crosses |
  |---|---|---|
  | `SimulationRequest`, `SimulationResponse` | `schemas.py` | the wire — pydantic, `frozen`, `extra="forbid"` |
  | `SimulationInput`, `SimulationResult`, `AmortisationSchedule`, `UpfrontCosts` | `entities.py` | service ↔ calculator |
  | `SimulationRow` | `tables.py` | never leaves the repository (CQ-088) |

  `calculator.py` takes `SimulationInput`, **not** `SimulationRequest`: a pure module may not import
  pydantic wire schemas (ARC-013), and the service is what converts between them. The two are
  deliberately different types with the same fields, and `10-implementation.md` T10 names the entity.

- **ARC-040** — Three files in a domain hold "models"; each gets a distinct word, and the words are
  used consistently everywhere:

  | File | Holds | Crosses which boundary |
  |---|---|---|
  | `tables.py` | SQLAlchemy table definitions | never leaves the repository |
  | `entities.py` | the domain model services and pure functions work with | repository ↔ service ↔ pure modules |
  | `schemas.py` | pydantic request and response models | service ↔ router ↔ the wire |

  `models` is not used as a filename: it is the word SQLAlchemy uses for its own classes, so it
  cannot distinguish the three.

- **ARC-046** — **`entities.py` holds frozen dataclasses; `schemas.py` holds pydantic models.** The
  tool is part of the distinction, not an accident of who wrote the file first.

  `1-code-quality.md` CQ-024 puts pydantic **at every boundary** — requests, responses, settings —
  and an entity is not a boundary: it carries data that has already been validated on the way in.
  Revalidating it at each internal hop buys nothing.

  The sharper reason is ARC-043. That rule exists so that `calculator.py` takes `SimulationInput` and
  not `SimulationRequest`. If entities were pydantic too, the two would be structurally identical
  models over the same fields, and "why are there two types?" would become a fair question with no
  good answer. Different tools keep the two roles legible: **a schema is untrusted input and
  validates; an entity is checked data and simply holds it.**

  This was left unstated until T12 and had to be inferred from the code, which is exactly the kind of
  silence `specs/README` says a spec should not contain.

## 12. Why not hexagonal / ports and adapters

**ARC-036.** Considered and rejected. With four entities and one database, the full
ports-and-adapters layout adds three indirection layers that carry no information. The two places the
pattern earns its keep are already covered by protocols: the repository protocols for data
(`1-code-quality.md` CQ-064, CQ-095) and `StorageBackend` for blobs. Swapping JSON files for SQLite
touched the repositories and nothing above them, which is the whole argument.

The `1-code-quality.md` rule applies (CQ-001): introduce an abstraction when it has a second
consumer. This one does not yet.

---

# Appendix A — Traceability

Source: `04-architecture.md`, superseded by this document.

| ID | Statement | Source § | § |
|---|---|---|---|
| ARC-001 | Organise by domain, not by technical layer | Principle | §1 |
| ARC-002 | The canonical backend tree | Backend | §2 |
| ARC-003 | Every domain has the same internal shape | Principle / Backend | §2 |
| ARC-004 | `router.py` owns routes, never logic | What each file owns | §3 |
| ARC-005 | `service.py` owns the flow, never maths or HTTP concepts | What each file owns | §3 |
| ARC-006 | `schemas.py` owns the wire contract | What each file owns | §3 |
| ARC-007 | `entities.py` owns the internal domain representation | What each file owns | §3 |
| ARC-008 | Pure modules own domain logic, import no framework | What each file owns | §3 |
| ARC-009 | `repository.py` owns the queries, never business rules | What each file owns | §3 |
| ARC-010 | Dependency direction; arrows point one way only | Dependency direction | §4 |
| ARC-011 | No cross-domain internals; go through `service.py` | Dependency direction, rule 1 | §4 |
| ARC-012 | `core` never imports from `domains` | Dependency direction, rule 2 | §4 |
| ARC-013 | Pure modules import stdlib, `decimal`, own `entities.py` only | Dependency direction, rule 3 | §4 |
| ARC-014 | `main.py` is the only file that knows all domains | Dependency direction, rule 4 | §4 |
| ARC-015 | Violating ARC-011 or ARC-012 is a design error | Dependency direction | §4 |
| ARC-016 | Exactly two cross-domain edges exist | Known cross-domain edges | §5 |
| ARC-017 | `auth.service` → `simulation.service.claim_for_user()` | Known cross-domain edges | §5 |
| ARC-018 | `documents.service` → `applications.service.recompute_status()` | Known cross-domain edges | §5 |
| ARC-019 | Both edges are one-directional service calls | Known cross-domain edges | §5 |
| ARC-020 | Frontend mirrors the backend domains and layering | Frontend | §6 |
| ARC-021 | A component never calls HTTP | Frontend rules, 1 | §7 |
| ARC-022 | Pages hold state, components receive inputs | Frontend rules, 2 | §7 |
| ARC-023 | `shared/` has no business logic and no domain imports | Frontend rules, 3 | §7 |
| ARC-024 | A domain does not import another domain's components | Frontend rules, 4 | §7 |
| ARC-025 | Standalone components throughout | Frontend rules, 5 | §7 |
| ARC-026 | Money is `string` end to end | Frontend rules, 6 | §7 |
| ARC-027 | Models mirror schemas field for field, no renaming layer | Model mirroring | §8 |
| ARC-028 | Four parallel units of work, no shared files | Ownership boundaries | §9 |
| ARC-029 | A and D start now; B needs A's signatures; C needs B's schemas | Ownership boundaries | §9 |
| ARC-030 | Only D edits `main.py`; only A edits a pure module | Ownership boundaries | §9 |
| ARC-031 | `POST /api/simulations` end to end | A request, end to end | §10 |
| ARC-032 | Python modules `snake_case`, singular concept / plural collection | Naming | §11 |
| ARC-033 | Domain folders take the plural of the aggregate | Naming | §11 |
| ARC-034 | Angular files are `<name>.<role>.ts` | Naming | §11 |
| ARC-035 | Test files mirror the module under test | Naming | §11 |
| ARC-036 | Hexagonal considered and rejected | Why not hexagonal | §12 |
| ARC-037 | The preset and `styles.css` are the only styling surfaces | added for `3-ui.md` §6.2 | §6 |
| ARC-038 | `tables.py` owns the SQLAlchemy table definitions | added for the SQLite switch | §3 |
| ARC-039 | `core/database.py` owns the connection and nothing else | added for the SQLite switch | §4 |
| ARC-040 | `tables` / `entities` / `schemas` naming | added for the SQLite switch | §11 |
| ARC-041 | Repo-root layout; `infra/` and `observability/` are config only | added for `5-deployment.md` | §2 |
| ARC-042 | `domains/auth/dependencies.py` is a second public surface | added for `6-auth.md` | §4 |
| ARC-043 | Simulation entity types vs wire schema types | added — resolves the `SimulationInput` gap | §11 |
| ARC-044 | `core/enums.py` holds the two cross-domain value enums | added — `DocumentType` had no single home | §4 |
| ARC-045 | `core/errors.py` is on the pure-module whitelist | added at T06 — CQ-054 and VAL-004 required what ARC-013 forbade | §4 |
| ARC-046 | `entities.py` is dataclasses, `schemas.py` is pydantic | added — the spec never said, so it had to be inferred | §11 |

## Superseded `CQ-` rules

These eleven rules moved here from `1-code-quality.md`. The ids survive there as one-line statements
pointing at their `ARC-` replacement — ids are superseded, never renumbered.

| Was | Now | Note |
|---|---|---|
| CQ-004 | ARC-001, ARC-002, ARC-003 | The tree here is canonical; it adds `entities.py`, `tables.py`, `core/dependencies.py`, `core/database.py`, `static/` and test filenames |
| CQ-005 | ARC-011 | ARC adds "injected as a dependency" |
| CQ-006 | ARC-012 | |
| CQ-007 | ARC-013 | **Corrected**: a whitelist (stdlib, `decimal`, own `entities.py`) replaces the old blacklist wording |
| CQ-008 | ARC-009 | Stated as file ownership rather than a standalone rule |
| CQ-009 | ARC-015 | |
| CQ-010 | ARC-020 | |
| CQ-011 | ARC-025 | |
| CQ-013 | ARC-027 | ARC adds the rationale against a renaming layer |
| CQ-015 | ARC-021 | |
| CQ-016 | ARC-010 | ARC adds the `core.errors` branch and the one-way constraint |

`CQ-012` (typed reactive forms) and `CQ-014` (money is `string`) stay in `1-code-quality.md`: they
are data representation, not structure. ARC-026 restates money in one line and points back.
