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
- [`specs/1-code-quality.md`](specs/1-code-quality.md) — structure, layering, typing, error handling,
  style. IDs: `CQ-`.

**Where the two disagree, the business spec wins.**

Before implementing: read the sections that govern the task and name the requirement IDs you are
implementing. Cite them in commit messages (`feat(sim): actuarial monthly rate — SIM-001, AC-002`).

## Hard rules

Violating one of these is a defect, not a style disagreement. Full text and reasoning in
`specs/1-code-quality.md`.

**Layering**
- A route handler contains **exactly one statement**: a single call to a service. No `if`, `for`,
  `while`, `try`; no repository or calculator call; no arithmetic or data shaping; no building a
  response field by field; no second service call. (CQ-017, CQ-018)
- Layers: router → service → (calculator | state machine | checklist) → repository. (CQ-016)
- A domain never imports another domain's internals — go through its `service.py`. `core` never
  imports from `domains`. Only `repository.py` touches storage. (CQ-005, CQ-006, CQ-008)
- `calculator.py`, `state_machine.py`, `checklist.py` are **pure**: nothing from the framework, the
  repository or the config, and entirely synchronous. (CQ-007, CQ-048)

**Typing**
- Every parameter and return annotated, including `-> None`. (CQ-020)
- **`Any` is forbidden in `app/`.** Allowed in `tests/`. (CQ-021, CQ-074)
- Pydantic v2 at every boundary, with `frozen=True, extra="forbid"`. (CQ-024 – CQ-026)
- Money: `Decimal` in Python, **`string` in TypeScript**, serialised as a string over JSON. Never
  `float`, never `number`. (CQ-014, CQ-027)

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
