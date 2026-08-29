---
id: CQ
title: Code Quality
status: draft
version: 1.0.0
owner: paketoff
updated: 2026-08-29
---

# 1 — Code Quality

Read [`0-business-logic.md`](0-business-logic.md) first: it defines what we are building and the
entities.

This document covers typing, error handling and style — **how code is written**. Where it lives and
what may import what is [`2-architecture.md`](2-architecture.md); that spec is canonical for the
folder tree, import boundaries and layering, and the rules below that moved there are kept as
one-line statements pointing at it.

It contains no business rules. **Where this spec and `0-business-logic.md` disagree, the business
spec wins.**

Rules carry stable `CQ-` ids and may be referenced from code, tests and commit messages. Appendix A
maps every id to its source section. Appendix B records what actually enforces each rule — a linter,
a hook, or review — because a rule no machine checks is an aspiration (CQ-079).

## 1. Philosophy

**Readability beats brevity. Simplicity beats flexibility.**

Code is written for the person who opens it in a month and for the model that has to change it.

- **CQ-001** — Introduce an abstraction when it has a second consumer, not because one might appear
  later. A clever one-liner that needs a comment loses to five obvious lines that do not.
- **CQ-002** — A single file handed to a model in isolation must be understandable without the rest
  of the repo. Both humans and models read this repository. That has consequences: names carry
  meaning, files stay small, dependencies are explicit.
- **CQ-003** — When two approaches both work, pick the one that is easier to delete.

## 2. Project structure

Canonical: [`2-architecture.md`](2-architecture.md) §2 – §8. These rules keep their ids and are
stated here in one line each so a reference from code or a commit still resolves.

- **CQ-004** — Organised by domain, not by technical layer; every domain has the same internal
  shape. → ARC-001, ARC-002, ARC-003
- **CQ-005** — A domain never imports another domain's internals. Cross-domain access goes through
  the other domain's `service.py`, injected as a dependency. → ARC-011
- **CQ-006** — `core` never imports from `domains`. The dependency points one way. → ARC-012
- **CQ-007** — Pure modules (`calculator.py`, `state_machine.py`, `checklist.py`) import only the
  standard library, `decimal`, and their own domain's `entities.py`. They never import SQLAlchemy or
  a session. → ARC-013
- **CQ-008** — `repository.py` is the only place that touches storage. → ARC-009
- **CQ-009** — If a change requires editing two domains, the boundary is drawn wrong. Say so rather
  than working around it. → ARC-015
- **CQ-010** — The frontend mirrors the backend: same domains, same layering. → ARC-020
- **CQ-011** — Standalone components. No `NgModule`. → ARC-025
- **CQ-012** — Typed reactive forms.
- **CQ-013** — Models mirror the pydantic schemas field for field, with no renaming layer.
  → ARC-027
- **CQ-014** — **Money is `string` on the frontend, never `number`.** JSON floats lose cents. Parse
  only for display; never round-trip through `number`. → ARC-026
- **CQ-015** — A component never calls HTTP directly. It calls its domain service. This is the
  frontend twin of the controller rule, CQ-017. → ARC-021

Only `CQ-012` and `CQ-014` are stated in full here: they are data representation, not structure.

## 3. Layering, and the controller rule

**CQ-016.** Four layers: router → service → (calculator | state machine | checklist) → repository.
The full dependency diagram, including the `core.errors` branch and the one-way constraint, is
canonical in [`2-architecture.md`](2-architecture.md) §4. → ARC-010

### 3.1 The controller rule

**CQ-017. A route handler contains exactly one statement: a single call to a service. No more, no
less.**

```python
@router.post("/simulations", response_model=SimulationResponse, status_code=201)
async def create_simulation(
    payload: SimulationRequest,
    service: SimulationService = Depends(get_simulation_service),
) -> SimulationResponse:
    """Create an anonymous mortgage simulation.

    Args:
        payload: Simulation inputs supplied by the borrower.
        service: Injected simulation service.

    Returns:
        The computed simulation, including payment, JKP and upfront costs.
    """
    return await service.create(payload)
```

**CQ-018.** Forbidden inside a route handler, without exception:

- `if`, `for`, `while`, `try`
- any call to a repository or a calculator
- any arithmetic or data shaping
- building a response object field by field
- more than one service call

**CQ-019.** Where the excluded work goes instead:

| Concern | Home |
|---|---|
| Input validation | pydantic schema |
| Authorisation | dependency |
| Business rules, orchestration | service |
| Domain error → HTTP status | global exception handler in `core/exception_handlers.py` |

This rule is not stylistic. It is what makes the service layer testable without a HTTP client, and it
is the first thing to check in review.

## 4. Typing

### 4.1 Python

- **CQ-020** — Every parameter and every return value is annotated, including `-> None`.
- **CQ-021** — **`Any` is forbidden in `app/`.** It is allowed in `tests/` (CQ-074). Use `object`, a
  `TypeVar`, a `Protocol`, or an explicit union instead.
- **CQ-022** — `# type: ignore` must name the error code and carry a one-line reason.
- **CQ-023** — Enforced, not suggested: `mypy --strict` with `disallow_any_explicit = true`.

### 4.2 Pydantic

**CQ-024.** Pydantic v2 at every boundary: requests, responses and settings. Persisted data crosses
its boundary as a domain entity built by the repository, not as a validated dict (CQ-088).

```python
class SimulationRequest(BaseModel):
    """Inputs for a mortgage simulation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    property_value: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    own_contribution: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    term_months: int = Field(ge=12, le=360)
    annual_nominal_rate: Decimal = Field(ge=0, le=Decimal("0.20"))
    region: Region
    is_first_home: bool
```

- **CQ-025** — `extra="forbid"`: an unexpected field is an error, not something silently dropped.
- **CQ-026** — `frozen=True` on request and response models. Mutating an input is how bugs hide.
- **CQ-027** — Money is `Decimal`, never `float`, and is serialised as a string. → `0-business-logic.md`
  DOM-003, SIM-021.

### 4.3 TypeScript

- **CQ-028** — `strict: true`, plus `noImplicitAny`, `strictNullChecks`, `noUncheckedIndexedAccess`.
- **CQ-029** — `@typescript-eslint/no-explicit-any` is set to `error`, relaxed only under `*.spec.ts`.

## 5. SOLID: S, I, D

**CQ-030.** Only these three are enforced. L and O are not useful at this size and invite speculative
abstraction.

### 5.1 Single responsibility

**CQ-031.** One module, one reason to change.

- `calculator.py` changes when the arithmetic changes.
- `service.py` changes when the flow changes.
- `repository.py` changes when storage changes.

**CQ-032.** If fixing one kind of bug means touching two files, the split is wrong.

### 5.2 Interface segregation

**CQ-033.** Interfaces are narrow. `StorageBackend` is `save` and `load`, not a general file manager.
A consumer that needs one method does not depend on a class with twelve.

### 5.3 Dependency inversion

**CQ-034.** Services depend on protocols, never on concrete implementations.

```python
class StorageBackend(Protocol):
    """Binary blob storage."""

    def save(self, key: str, content: bytes, content_type: str) -> str:
        """Persist content and return its storage key."""
        ...

    def load(self, key: str) -> bytes:
        """Retrieve content by storage key."""
        ...
```

`LocalStorage` implements it now. Swapping in S3 with presigned URLs is a new class and a changed
dependency provider, with no edit to any service.

**CQ-035.** Injection happens through FastAPI `Depends`. A service never imports a concrete
implementation directly.

## 6. Functions

- **CQ-036** — Soft limit 30 lines, hard limit 50, excluding the docstring.
- **CQ-037** — Beyond that the function becomes an orchestrator and the work moves into named
  helpers.
- **CQ-038** — Maximum four positional parameters. Beyond that, take a pydantic model.
- **CQ-039** — Nesting no deeper than three levels. Use early returns.
- **CQ-040** — No boolean flag parameters. Split the function, or take an enum.

```python
def simulate(request: SimulationRequest) -> SimulationResult:
    """Run a full mortgage simulation.

    Args:
        request: Validated borrower inputs.

    Returns:
        Payment figures, JKP, and the upfront cash breakdown.
    """
    loan = compute_loan_amount(request)
    schedule = build_amortisation_schedule(loan, request.term_months, request.annual_nominal_rate)
    upfront = compute_upfront_costs(request, loan)
    jkp = compute_jkp(loan, schedule.monthly_payment, request.term_months, upfront.jkp_fees)
    return assemble_result(request, loan, schedule, upfront, jkp)
```

The body reads as a table of contents, and every step is independently testable.

## 7. No lambdas

**CQ-041.** Anonymous functions are forbidden where a named function would work.

```python
# no
sorted(documents, key=lambda d: d.uploaded_at)
matched = list(filter(lambda d: d.doc_type == wanted, documents))

# yes
from operator import attrgetter

sorted(documents, key=attrgetter("uploaded_at"))
matched = [doc for doc in documents if doc.doc_type == wanted]
```

**CQ-042.** Comprehensions are preferred over `map` and `filter` entirely.

**CQ-043. Frontend exception, stated openly:** arrow functions inside RxJS pipes and Angular
templates cannot be removed without hurting readability and fighting the framework. The rule there
is: *named functions instead of anonymous ones wherever the callback is more than a single
expression.* A multi-line arrow in a `subscribe` becomes a named method on the component.

## 8. Docstrings

**CQ-044.** Google style. Required on every module, public class and public function. Private helpers
get a single line.

```python
def monthly_rate(annual_rate: Decimal) -> Decimal:
    """Convert a Belgian annual mortgage rate to its monthly periodic rate.

    Belgian mortgage credit derives the annual rate from the periodic rate
    actuarially: (1 + i) ** 12 == 1 + I. Dividing by twelve is the consumer
    credit convention and produces a payment that is too high.

    Args:
        annual_rate: Nominal annual rate as a fraction, e.g. Decimal("0.04").

    Returns:
        The monthly periodic rate, unrounded.

    Raises:
        ValueError: If annual_rate is negative.
    """
```

**CQ-045. A docstring explains why, not what the signature already says.** `"""Return the user."""`
above `get_user` is noise and should be deleted or replaced with something informative.

**CQ-046.** Every module opens with one or two lines stating what it owns. That header is also the
fastest orientation a model gets when handed the file alone (CQ-002).

## 9. Async

**CQ-047.** Async where there is IO to wait on: file reads and writes, outbound HTTP. Synchronous
everywhere else.

**Mortgage maths is CPU-bound.** Solving JKP by bisection runs a few hundred `Decimal` iterations;
building the amortisation schedule runs 300 steps. Inside an `async def` this blocks the event loop
for every other request. Therefore:

- **CQ-048** — `calculator.py` is entirely synchronous. It is called from async services as a normal
  function.
- **CQ-049** — If a calculation grows heavy enough to matter, it moves behind
  `await run_in_threadpool(...)` rather than becoming `async def`.

**CQ-050.** Forbidden:

- `time.sleep` inside async code
- synchronous HTTP clients inside `async def`
- `async def` with no `await` in the body

**CQ-051.** Frontend: no heavy synchronous loops in the main thread or in template expressions. HTTP
through RxJS. Template expressions stay cheap because they re-evaluate on every change detection
cycle.

## 10. Error handling

**CQ-052. Catch an exception only when you can do something with it:** translate it into a domain
error, add context, restore state, or return a meaningful fallback. Everything else propagates to the
global handler.

**CQ-053.** Domain errors carry a stable machine-readable code and a human message. HTTP mapping
happens once, in `core/exception_handlers.py`, never in a router (CQ-019).

### 10.1 Where a try block is warranted

**CQ-054. Numeric computation that can raise low-level errors:**

```python
def compute_jkp(
    loan_amount: Decimal,
    monthly_payment: Decimal,
    term_months: int,
    fees: Decimal,
) -> Decimal:
    """Solve for the all-in annual cost (JKP/TAEG) by bisection."""
    try:
        return _bisect_for_effective_rate(loan_amount, monthly_payment, term_months, fees)
    except (InvalidOperation, DivisionByZero, Overflow) as exc:
        raise SimulationError(
            code="JKP_COMPUTATION_FAILED",
            message="Could not solve for the effective annual rate.",
        ) from exc
```

`Decimal` raises errors that mean nothing to an API consumer. Translating them is real work.

**CQ-055. The boundary with the outside world:**

```python
async def list_documents(session: AsyncSession, application_id: UUID) -> list[Document]:
    """Load an application's documents, translating storage failures."""
    try:
        rows = await session.scalars(
            select(DocumentRow).where(DocumentRow.application_id == application_id)
        )
    except OperationalError as exc:
        raise StorageError(code="STORAGE_UNAVAILABLE") from exc

    try:
        return [to_entity(row) for row in rows]
    except (ValidationError, InvalidOperation) as exc:
        raise StorageError(code="STORAGE_CORRUPT", detail=str(application_id)) from exc
```

Two separate blocks because the two failures mean different things and deserve different handling: an
unreachable database is not the same as a row that cannot be turned into a domain entity. Note the
mapping to a domain entity happens here, inside the repository — CQ-088.

**CQ-056. File upload, where the client controls the input:**

```python
try:
    content = await upload.read()
except Exception as exc:
    raise DocumentError(code="UPLOAD_READ_FAILED") from exc
```

### 10.2 Where a try block is wrong

**CQ-057.** Each of these is a defect, not a style preference:

```python
# swallows a real bug and returns a silent lie
try:
    return compute_monthly_payment(loan, rate, term)
except Exception:
    return Decimal("0")

# catches and re-raises the same thing, adding nothing
try:
    return repository.get(simulation_id)
except NotFoundError:
    raise NotFoundError(simulation_id)

# error mapping does not belong in a controller
@router.post("/simulations")
async def create_simulation(payload: SimulationRequest):
    try:
        return await service.create(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

# defensive wrapping of code that cannot raise
try:
    total = price - contribution
except Exception:
    total = Decimal("0")
```

### 10.3 Hard rules

- **CQ-058** — Never a bare `except:`.
- **CQ-059** — Never `except Exception` without re-raising something more specific.
- **CQ-060** — Always `raise ... from exc`, so the cause survives.
- **CQ-061** — Never log and swallow. Log and re-raise, or handle it properly.
- **CQ-062** — Error responses never leak stack traces or internal paths.

### 10.4 Error codes

**CQ-063.** Stable strings, defined in one place, used by both backend and frontend:

`LOAN_AMOUNT_NOT_POSITIVE`, `TERM_OUT_OF_RANGE`, `RATE_OUT_OF_RANGE`,
`JKP_COMPUTATION_FAILED`, `UNSUPPORTED_DOCUMENT_TYPE`, `DOCUMENT_TOO_LARGE`,
`INVALID_STATE_TRANSITION`, `STORAGE_UNAVAILABLE`, `STORAGE_CORRUPT`,
`UPLOAD_READ_FAILED`, `EMAIL_ALREADY_REGISTERED`.

Five of these are also fixed by the business spec (`0-business-logic.md` ERR-002); the remaining six
are introduced here and are infrastructure concerns.

`STORAGE_UNAVAILABLE` and `STORAGE_CORRUPT` cover **database** failures — an unreachable or locked
database, a row that cannot be mapped to a domain entity. They kept their names through the move off
JSON files because the meaning is the same: the store failed, and the API consumer cannot act on the
detail. `EMAIL_ALREADY_REGISTERED` is what an `IntegrityError` on the unique email constraint maps to
(CQ-092).

## 11. Persistence

**CQ-064.** SQLite, behind a repository protocol. The protocol is unchanged from the JSON era, and
that is the point — see CQ-095.

```python
class SimulationRepository(Protocol):
    """Persistence for simulations."""

    async def save(self, session: AsyncSession, simulation: Simulation) -> Simulation: ...
    async def get(self, session: AsyncSession, simulation_id: UUID) -> Simulation | None: ...
```

`Simulation` here is the domain entity from `entities.py`, never a SQLAlchemy row (CQ-088).

### 11.1 Engine and session

- **CQ-080** — SQLAlchemy 2.0 with async support, `aiosqlite` driver.
- **CQ-081** — Database URL `sqlite+aiosqlite:///${DATA_DIR}/app.db`. `DATA_DIR` defaults to `/data`.
- **CQ-082** — The schema is created at startup with `create_all()`. **No Alembic.** Migrations are
  a deliberate cut for this build, not an oversight: one environment, one schema, no data to
  preserve. Adding them later is additive.
- **CQ-083** — Async sessions are handed out by a FastAPI dependency, one session per request.
- **CQ-084** — Pragmas applied on connect: `foreign_keys=ON` and `journal_mode=WAL`.

Connection ownership lives in `core/database.py` and nowhere else — `2-architecture.md` ARC-039.

### 11.2 Tables

**CQ-085.** Five tables, mirroring the entities in `0-business-logic.md` §9:

| Table | Keys and indexes |
|---|---|
| `users` | unique index on `email` (case-insensitive, DOM-019) |
| `simulations` | nullable `user_id` FK, index on `user_id` |
| `applications` | `user_id` FK, nullable `simulation_id` FK |
| `borrowers` | `application_id` FK |
| `documents` | `application_id` FK, index on `application_id` and `doc_type` |

`borrowers` is **a real table, not a JSON column.** Most Belgian mortgages are joint (DOM-021), and a
one-to-many from application to borrower is exactly the relation a relational model exists for.

Definitions live in each domain's `tables.py` — `2-architecture.md` ARC-038, ARC-040.

- **CQ-086** — Money columns are `Numeric(12, 2)`, read as `Decimal`, **never** `float`. Not
  negotiable; it is CQ-003 enforced at the storage layer.
- **CQ-087** — `Application.status` remains a stored column. There is no computed-status workaround
  to keep: status transitions are written inside the same transaction as the change that caused them.

### 11.3 The ORM boundary

- **CQ-088** — **The ORM boundary is the repository.** A domain entity or primitives go in; a domain
  entity comes out. A SQLAlchemy instance never crosses it — never into a service, a response schema
  or a template.
- **CQ-089** — **No lazy loading outside the repository.** The session may already be closed, and
  that is a classic source of mysterious errors. The repository loads what it needs explicitly with
  `selectinload` and returns a fully populated object.
- **CQ-090** — The session is injected into the service as a dependency and passed down to the
  repository. A repository never creates a session.
- **CQ-091** — **The service owns the transaction boundary, not the repository.** A service may call
  several repositories inside one transaction — which is exactly what document upload needs, where a
  `Document` is created and the `Application` changes status atomically (ARC-018, APP-003, APP-004).
  A repository that committed would make that transaction impossible.
- **CQ-092** — Uniqueness is enforced by a database constraint, not only by a check in code. The
  check produces a readable message; the constraint produces correctness. `IntegrityError` is caught
  and mapped to a domain error (`EMAIL_ALREADY_REGISTERED`).
- **CQ-093** — **No raw SQL in services.** `select()`, `insert()`, `update()` and `delete()` appear
  only in `repository.py`.
- **CQ-067** — Repositories return domain entities, never rows and never raw dicts.
- **CQ-068** — Only `repository.py` knows the storage format.
- **CQ-094** — Cross-domain access still goes through the other domain's `service.py`, never its
  repository. The rule from `2-architecture.md` ARC-011 survives the switch to SQLite unchanged.

### 11.4 Why the swap was cheap

**CQ-095.** Services depend on repository protocols, never on SQLAlchemy (CQ-034). That decision was
made before the storage backend was chosen, and it is the reason moving from JSON files to SQLite
touched the repositories and nothing above them. Keep it: the next backend change should be equally
cheap.

### 11.5 Withdrawn

Ids are stable — a withdrawn rule keeps its number and its reason so an older commit message still
resolves.

- **CQ-065 — withdrawn.** *Writes are atomic: temporary file in the same directory, then
  `os.replace`.* Superseded by SQLite transactions (CQ-091).
- **CQ-066 — withdrawn.** *A single asyncio lock guards writes.* Superseded by WAL and SQLite's own
  locking (CQ-084).

### 11.6 Known limitation

**CQ-069. To be stated in the README:** the container filesystem is ephemeral, so unless `DATA_DIR`
is a mounted volume neither `app.db` nor the uploaded blobs survive a restart. That is acceptable for
a demo with fake test data. The caveat outlived the JSON store because both artefacts still live on
the filesystem — only its subject changed.

## 12. Tests

- **CQ-070** — Strict test-first on pure domain logic: the calculator, the state machine, the
  checklist generator. Those are where correctness is not recoverable by good structure.
- **CQ-071** — Integration tests after the fact on the CRUD surface, and only a few: create a
  simulation, sign up, submit an application, upload a document.
- **CQ-072** — Naming: `test_<subject>_<condition>_<expectation>`.
- **CQ-073** — No mocks where a real object will do. Mock the storage backend, not the calculator.
- **CQ-074** — `Any` is allowed here.
- **CQ-075** — The acceptance criteria `AC-001` – `AC-008` in `0-business-logic.md` §20 are the test
  suite, not a suggestion.

## 13. Tooling

Rules that a machine does not check are aspirations. These are enforced in pre-commit and in CI.

- **CQ-076. Python** — `ruff` with: `ANN` (annotations), `D` with the google convention (docstrings),
  `C901` (complexity), `PLR0913` (argument count), `E501` at 100 characters.
- **CQ-077** — Plus `mypy --strict` with `disallow_any_explicit = true`.
- **CQ-078. TypeScript** — ESLint with `@typescript-eslint/no-explicit-any` as `error`, plus
  `@typescript-eslint/explicit-function-return-type`. Prettier for formatting.
- **CQ-079. Definition of done for any unit of work:** the linter is green, `mypy --strict` is clean,
  and the tests pass. Not "it runs".

---

# Appendix A — Traceability

Source: `03-code-quality.md`, superseded by this document.

| ID | Statement | Source § | § |
|---|---|---|---|
| CQ-001 | Abstraction only with a second consumer | 1 Philosophy | §1 |
| CQ-002 | A file must be understandable in isolation | 1 Philosophy | §1 |
| CQ-003 | Prefer the option that is easier to delete | 1 Philosophy | §1 |
| CQ-004 | Backend organised by domain, not by layer | 2 Backend | §2 — moved to `2-architecture.md` ARC-001 – ARC-003 |
| CQ-005 | No cross-domain internals; go through `service.py` | 2 Import rules | §2 — moved to `2-architecture.md` ARC-011 |
| CQ-006 | `core` never imports from `domains` | 2 Import rules | §2 — moved to `2-architecture.md` ARC-012 |
| CQ-007 | Calculator, state machine, checklist are pure | 2 Import rules | §2 — moved to `2-architecture.md` ARC-013 |
| CQ-008 | Only `repository.py` touches storage | 2 Import rules | §2 — moved to `2-architecture.md` ARC-009 |
| CQ-009 | Editing two domains means the boundary is wrong | 2 Import rules | §2 — moved to `2-architecture.md` ARC-015 |
| CQ-010 | Frontend mirrors the backend domains | 2 Frontend | §2 — moved to `2-architecture.md` ARC-020 |
| CQ-011 | Standalone components, no `NgModule` | 2 Frontend | §2 — moved to `2-architecture.md` ARC-025 |
| CQ-012 | Typed reactive forms | 2 Frontend | §2.3 |
| CQ-013 | TS models mirror pydantic schemas field for field | 2 Frontend | §2 — moved to `2-architecture.md` ARC-027 |
| CQ-014 | Money is `string` on the frontend | 2 Frontend | §2.3 |
| CQ-015 | A component never calls HTTP directly | 2 Frontend | §2 — moved to `2-architecture.md` ARC-021 |
| CQ-016 | Four layers | 3 Layering | §3 — moved to `2-architecture.md` ARC-010 |
| CQ-017 | **The controller rule** — one statement per handler | 3 The controller rule | §3.1 |
| CQ-018 | Five things forbidden in a route handler | 3 The controller rule | §3.1 |
| CQ-019 | Where the excluded work goes | 3 The controller rule | §3.1 |
| CQ-020 | Every parameter and return annotated | 4 Python | §4.1 |
| CQ-021 | `Any` forbidden in `app/` | 4 Python | §4.1 |
| CQ-022 | `# type: ignore` names its code and reason | 4 Python | §4.1 |
| CQ-023 | `mypy --strict`, `disallow_any_explicit` | 4 Python | §4.1 |
| CQ-024 | Pydantic v2 at every boundary | 4 Pydantic | §4.2 |
| CQ-025 | `extra="forbid"` | 4 Pydantic | §4.2 |
| CQ-026 | `frozen=True` on request and response models | 4 Pydantic | §4.2 |
| CQ-027 | Money is `Decimal`, serialised as string | 4 Pydantic | §4.2 |
| CQ-028 | TS `strict` plus three extra flags | 4 TypeScript | §4.3 |
| CQ-029 | `no-explicit-any` = error, relaxed in `*.spec.ts` | 4 TypeScript | §4.3 |
| CQ-030 | Only S, I and D are enforced | 5 SOLID | §5 |
| CQ-031 | One module, one reason to change | 5 Single responsibility | §5.1 |
| CQ-032 | One bug touching two files means a wrong split | 5 Single responsibility | §5.1 |
| CQ-033 | Narrow interfaces | 5 Interface segregation | §5.2 |
| CQ-034 | Services depend on protocols | 5 Dependency inversion | §5.3 |
| CQ-035 | Injection through `Depends` | 5 Dependency inversion | §5.3 |
| CQ-036 | 30 lines soft, 50 hard | 6 Functions | §6 |
| CQ-037 | Beyond the limit, orchestrate named helpers | 6 Functions | §6 |
| CQ-038 | Max four positional parameters | 6 Functions | §6 |
| CQ-039 | Nesting ≤ 3, early returns | 6 Functions | §6 |
| CQ-040 | No boolean flag parameters | 6 Functions | §6 |
| CQ-041 | No anonymous function where a named one works | 7 No lambdas | §7 |
| CQ-042 | Comprehensions over `map` and `filter` | 7 No lambdas | §7 |
| CQ-043 | Frontend exception for RxJS and templates | 7 No lambdas | §7 |
| CQ-044 | Google docstrings, required where public | 8 Docstrings | §8 |
| CQ-045 | A docstring explains why | 8 Docstrings | §8 |
| CQ-046 | Every module opens with what it owns | 8 Docstrings | §8 |
| CQ-047 | Async only where there is IO | 9 Async | §9 |
| CQ-048 | `calculator.py` is entirely synchronous | 9 Async | §9 |
| CQ-049 | Heavy maths goes to `run_in_threadpool` | 9 Async | §9 |
| CQ-050 | Three forbidden async patterns | 9 Async | §9 |
| CQ-051 | Frontend: cheap template expressions, RxJS HTTP | 9 Async | §9 |
| CQ-052 | Catch only when you can do something with it | 10 Error handling | §10 |
| CQ-053 | HTTP mapping once, in the exception handler | 10 Error handling | §10 |
| CQ-054 | Warranted: numeric computation | 10 Where warranted | §10.1 |
| CQ-055 | Warranted: the boundary with the outside world | 10 Where warranted | §10.1 |
| CQ-056 | Warranted: client-controlled file upload | 10 Where warranted | §10.1 |
| CQ-057 | Four patterns that are wrong | 10 Where wrong | §10.2 |
| CQ-058 | Never a bare `except:` | 10 Hard rules | §10.3 |
| CQ-059 | Never `except Exception` without a re-raise | 10 Hard rules | §10.3 |
| CQ-060 | Always `raise ... from exc` | 10 Hard rules | §10.3 |
| CQ-061 | Never log and swallow | 10 Hard rules | §10.3 |
| CQ-062 | No stack traces or internal paths in responses | 10 Hard rules | §10.3 |
| CQ-063 | Eleven stable error codes in one place | 10 Error codes | §10.4 |
| CQ-064 | SQLite behind a repository protocol | 11 Persistence | §11 |
| CQ-065 | ~~Atomic writes via `os.replace`~~ — **withdrawn**, superseded by CQ-091 | 11 Persistence | §11.5 |
| CQ-066 | ~~A single asyncio lock guards writes~~ — **withdrawn**, superseded by CQ-084 | 11 Persistence | §11.5 |
| CQ-067 | Repositories return domain entities, never rows | 11 Persistence | §11.3 |
| CQ-068 | Only `repository.py` knows the storage format | 11 Persistence | §11.3 |
| CQ-069 | Ephemeral filesystem stated in the README | 11 Persistence | §11.6 |
| CQ-070 | Test-first on pure domain logic | 12 Tests | §12 |
| CQ-071 | A few integration tests, after the fact | 12 Tests | §12 |
| CQ-072 | `test_<subject>_<condition>_<expectation>` | 12 Tests | §12 |
| CQ-073 | No mocks where a real object will do | 12 Tests | §12 |
| CQ-074 | `Any` allowed in tests | 12 Tests | §12 |
| CQ-075 | The acceptance criteria are the test suite | 12 Tests | §12 |
| CQ-076 | ruff: `ANN`, `D`, `C901`, `PLR0913`, `E501` at 100 | 13 Tooling | §13 |
| CQ-077 | `mypy --strict`, `disallow_any_explicit` | 13 Tooling | §13 |
| CQ-078 | ESLint rules plus Prettier | 13 Tooling | §13 |
| CQ-079 | Definition of done: green, clean, passing | 13 Tooling | §13 |
| CQ-080 | SQLAlchemy 2.0 async with `aiosqlite` | SQLite switch | §11.1 |
| CQ-081 | `sqlite+aiosqlite:///${DATA_DIR}/app.db`, `DATA_DIR` = `/data` | SQLite switch | §11.1 |
| CQ-082 | `create_all()` at startup; no Alembic, migrations cut | SQLite switch | §11.1 |
| CQ-083 | One async session per request, from a dependency | SQLite switch | §11.1 |
| CQ-084 | Pragmas `foreign_keys=ON`, `journal_mode=WAL` | SQLite switch | §11.1 |
| CQ-085 | The five tables, their keys and indexes | SQLite switch | §11.2 |
| CQ-086 | Money columns are `Numeric(12, 2)`, read as `Decimal` | SQLite switch | §11.2 |
| CQ-087 | `Application.status` remains a stored column | SQLite switch | §11.2 |
| CQ-088 | The ORM boundary is the repository | SQLite switch | §11.3 |
| CQ-089 | No lazy loading outside the repository; use `selectinload` | SQLite switch | §11.3 |
| CQ-090 | The session is injected, never created by a repository | SQLite switch | §11.3 |
| CQ-091 | The service owns the transaction boundary | SQLite switch | §11.3 |
| CQ-092 | Uniqueness by database constraint; `IntegrityError` mapped | SQLite switch | §11.3 |
| CQ-093 | No raw SQL in services | SQLite switch | §11.3 |
| CQ-094 | Cross-domain access still goes through `service.py` | SQLite switch | §11.3 |
| CQ-095 | Protocols are why the swap was cheap | SQLite switch | §11.4 |

# Appendix B — Enforcement map

What actually checks each rule. `review` means no tool proves it: it is caught by an agent following
[`.claude/skills/code-quality`](../.claude/skills/code-quality/SKILL.md), by
`code-quality-reviewer`, or by a human — and nowhere else.

Per-edit hooks are a local convenience and are not committed. Nothing in this table depends on them:
the binding enforcement is pre-commit and CI (CQ-076 – CQ-079).

| Enforced by | Rules |
|---|---|
| `ruff:ANN` | CQ-020 |
| `ruff:D` (google) | CQ-044 |
| `ruff:C901` | CQ-039 (partly — complexity, not nesting depth) |
| `ruff:PLR0913` | CQ-038 |
| `ruff:E501` | line length, CQ-076 |
| `ruff:E722` | CQ-058 (bare `except:`) |
| `mypy --strict` | CQ-020, CQ-021, CQ-022, CQ-023, CQ-027 (`Decimal` vs `float`) |
| `eslint` | CQ-029, CQ-028 (via `tsc`), CQ-078 |
| `hook` *(local, not committed)* | an editor or agent hook may run the same tools per file; convenience only |
| `CI` / `pre-commit` | the binding gate — the same ruff, mypy and eslint runs, on every change |
| **`review`** | **CQ-001 – CQ-019** (philosophy, structure, import boundaries, the controller rule), CQ-024 – CQ-026, CQ-030 – CQ-037, CQ-040 – CQ-043, CQ-045, CQ-046, CQ-047 – CQ-057, CQ-059 – CQ-075 |

The two rules the source calls load-bearing — the controller rule (CQ-017) and the import boundaries
(CQ-005 – CQ-008) — are not expressible in ruff. They are `review`. That asymmetry is the reason the
skill, the command and the reviewer agent exist, rather than the hooks alone.
