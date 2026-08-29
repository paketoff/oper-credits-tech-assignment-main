# oper-credits — agent instructions

Borrower portal for a Belgian mortgage lender. Spec-driven: `specs/` is the source of truth, code
follows.

| Area | Stack |
|---|---|
| `backend/` | Python 3.12 + FastAPI |
| `frontend/` | Angular + TypeScript |
| `infra/` | Docker |
| `observability/` | LGTM (Loki, Grafana, Tempo, Mimir) |

## Specs

- [`specs/0-business-logic.md`](specs/0-business-logic.md) — scope, domain model, lifecycle, and the
  simulation engine specified to the cent. IDs: `SCP- DOM- DOC- APP- SIM- ERR- AC-`.
- [`specs/1-code-quality.md`](specs/1-code-quality.md) — typing, error handling, style: how code is
  written. IDs: `CQ-`.
- [`specs/2-architecture.md`](specs/2-architecture.md) — where code lives and what may import what:
  the folder tree, import boundaries, layering, naming. IDs: `ARC-`.
- [`specs/3-ui.md`](specs/3-ui.md) — what the frontend looks like: tokens, type, Tailwind and PrimeNG
  rules, components. IDs: `UI-`.
- [`specs/4-ux.md`](specs/4-ux.md) — how it behaves: flows, timing, states. IDs: `UX-`.

**The business spec wins over both.** For structure and imports, `2-architecture.md` is canonical
and `1-code-quality.md` points at it.

Before implementing: read the sections that govern the task and name the requirement IDs you are
implementing. Cite them in commit messages (`feat(sim): actuarial monthly rate — SIM-001, AC-002`).

## Hard rules

Violating one of these is a defect, not a style disagreement. Full text and reasoning in
`specs/1-code-quality.md`.

**Layering**
- A route handler contains **exactly one statement**: a single call to a service. No `if`, `for`,
  `while`, `try`; no repository or calculator call; no arithmetic or data shaping; no building a
  response field by field; no second service call. (CQ-017, CQ-018)
- Layers: router → service → (calculator | state machine | checklist) → repository →
  `core.database` for rows, `core.storage` for uploaded blobs. Arrows point one way only. (ARC-010)
- A domain never imports another domain's internals — go through its `service.py`, injected as a
  dependency. `core` never imports from `domains`. Only `repository.py` touches storage. `main.py` is
  the only file that knows all domains. (ARC-011 – ARC-014)
- `calculator.py`, `state_machine.py`, `checklist.py` are **pure**: they import only the standard
  library, `decimal`, and their own domain's `entities.py` — never SQLAlchemy or a session — and are
  entirely synchronous. (ARC-013, CQ-048)
- **Exactly two cross-domain calls are legal**, both one-directional service calls:
  `auth.service → simulation.service.claim_for_user()` and
  `documents.service → applications.service.recompute_status()`. Do not invent a third — if a feature
  seems to need one, the boundary is drawn wrong. (ARC-016 – ARC-019, ARC-015)
- Organise by domain, never by technical layer. Files go where `2-architecture.md` §2 puts them.
  (ARC-001, ARC-002)

**Persistence** — SQLite via SQLAlchemy 2.0 async (`aiosqlite`)
- **The ORM boundary is the repository.** A SQLAlchemy row never reaches a service, a response schema
  or a template; the repository maps it to an entity. No lazy loading outside the repository — load
  with `selectinload`. (CQ-088, CQ-089)
- **The service owns the transaction, not the repository.** A repository never commits and never
  creates a session; the session is injected and passed down. This is what lets one upload create a
  `Document` and move the `Application` status atomically. (CQ-090, CQ-091)
- `select`/`insert`/`update`/`delete` appear only in `repository.py`. No raw SQL in a service.
  (CQ-093)
- Money columns are `Numeric(12, 2)`, read as `Decimal`, never `float`. (CQ-086)
- Three model files per domain, three distinct words: `tables.py` (SQLAlchemy), `entities.py`
  (domain), `schemas.py` (pydantic). (ARC-040)

**Typing
- Every parameter and return annotated, including `-> None`. (CQ-020)
- **`Any` is forbidden in `app/`.** Allowed in `tests/`. (CQ-021, CQ-074)
- Pydantic v2 at every boundary, with `frozen=True, extra="forbid"`. (CQ-024 – CQ-026)
- Money: `Decimal` in Python, **`string` in TypeScript**, serialised as a string over JSON. Never
  `float`, never `number`; parse only for display. (CQ-014, CQ-027, ARC-026)

**Frontend structure**
- A component never calls HTTP — it calls its domain service. Pages hold state; components under
  `components/` take `@Input` and emit `@Output` and inject nothing. `shared/` has no business logic
  and no domain imports. Standalone components, no `NgModule`. (ARC-021 – ARC-025)

**Frontend styling** — these four are what gets violated first:
- **Every `*.component.css` stays empty.** If one has content, the work is not done. (UI-027)
- **No `@apply` outside `@layer base` in `src/styles.css`.** If a class list repeats, extract a
  component, not a CSS class. (UI-028)
- **No hex anywhere outside `@theme`.** Colours are tokens: `bg-accent`, not `bg-[#0B5D5B]`, not
  `text-teal-700`. Spacing comes from the scale: `p-4`, never `p-[13px]`. (UI-030, UI-031, UI-064)
- **No `[ngStyle]`, no `style="..."`.** Dynamic styling is `[class]` with whole utility strings.
  (UI-029)
- PrimeNG is used for exactly four components — stepper, fileupload, inputnumber, select. Everything
  else is a plain element with utilities. Appearance is changed in the preset, never with a CSS
  override. (UI-036, UI-037, ARC-037)

**Frontend behaviour**
- The simulator opens with a computed result from a prefilled form — never a blank form or a
  calculate button — and the previous result stays on screen while a new one loads. (UX-009, UX-013)
- Error text comes from backend error codes and appears beside its field, never as a toast, never
  hardcoded in a template. (UX-023, UX-024)

**Functions**
- ≤30 lines soft, 50 hard, excluding the docstring. ≤4 positional parameters. Nesting ≤3, use early
  returns. No boolean flag parameters. (CQ-036 – CQ-040)
- No lambdas where a named function would work; comprehensions over `map`/`filter`. Frontend
  exception: RxJS pipes and templates, but a multi-line arrow becomes a named method. (CQ-041 – CQ-043)

**Errors**
- Catch only when you can **do** something: translate, add context, restore state, or return a
  meaningful fallback. Otherwise let it propagate to the global handler. (CQ-052)
- Never a bare `except:`. Never `except Exception` without re-raising something more specific. Always
  `raise ... from exc`. Never log and swallow. Never leak stack traces or internal paths.
  (CQ-058 – CQ-062)
- Domain error → HTTP status is mapped once, in `core/exception_handlers.py`, never in a router.
  (CQ-053)

**Docstrings**
- Google style on every module, public class and public function; one line for private helpers. A
  docstring explains **why**, not what the signature already says. (CQ-044, CQ-045)

**Tests**
- Test-first on pure domain logic (calculator, state machine, checklist). The acceptance criteria
  `AC-001` – `AC-008` are the test suite, not a suggestion. (CQ-070, CQ-075)
- Naming: `test_<subject>_<condition>_<expectation>`. Mock the storage backend, not the calculator.
  (CQ-072, CQ-073)

## Definition of done

The linter is green, `mypy --strict` is clean, and the tests pass. Not "it runs". (CQ-079)

Run the gate yourself before reporting done — nothing runs it for you.

No linter can check layering, import boundaries, the controller rule, or whether a `try` block is
warranted. See Appendix B of `specs/1-code-quality.md` for what is machine-checked and what is not.
Those are on you.
