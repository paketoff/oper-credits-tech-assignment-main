---
name: code-quality
description: Apply this project's code-quality rules (specs/1-code-quality.md, CQ-001..CQ-079) when writing or editing any Python under backend/ or any TypeScript/Angular under frontend/. Use when implementing a domain, adding a route, service, calculator, repository, pydantic schema, Angular component or service, writing tests, or reviewing a diff in this repo. Covers layering and the controller rule, import boundaries, typing, function limits, error handling, docstrings, async, and persistence.
---

# Code quality — how to apply the rules

The rules live in [`specs/1-code-quality.md`](../../../specs/1-code-quality.md) (how code is
written, `CQ-`), [`specs/2-architecture.md`](../../../specs/2-architecture.md) (where it lives and
what may import what, `ARC-`), and for frontend work
[`specs/3-ui.md`](../../../specs/3-ui.md) (`UI-`) and [`specs/4-ux.md`](../../../specs/4-ux.md)
(`UX-`). This file is the procedure, not a second copy of them — referencing by id keeps one source
of truth.

## Before writing code

1. **Identify what you are touching**: a domain (`simulation`, `applications`, `documents`, `auth`),
   `core/`, or the frontend.
2. **Read `specs/2-architecture.md` §2 – §5** — the tree, what each file owns, the dependency
   direction and the two legal cross-domain edges. Those decide *where* code goes and are expensive
   to fix afterwards. Then read the sections of `specs/1-code-quality.md` that govern how you write
   it.
   **For any frontend work**, also read `specs/3-ui.md` §5 (the nine Tailwind rules) before writing a
   single template, and the `4-ux.md` section covering the screen you are building.
3. **Read the business spec** for any rule that overrides: `specs/0-business-logic.md`. It wins on
   every disagreement.
4. **Name the requirement IDs** you are implementing, business (`SIM-`, `DOM-`, …) and code (`CQ-`).

## Where code goes

```
router.py      routes only — one statement per handler (CQ-017, ARC-004)
service.py     the flow: validate, call pure functions, persist, assemble (ARC-005)
               owns the transaction boundary (CQ-091)
schemas.py     the wire contract in and out (ARC-006)
entities.py    internal domain representation (ARC-007)
tables.py      SQLAlchemy table definitions (ARC-038)
calculator.py  pure maths, no IO, synchronous (ARC-013, CQ-048)
state_machine.py  pure — owns the allowed transitions (APP-009)
checklist.py   pure — derives the required document set (DOC-005)
repository.py  the queries, and the ORM boundary (ARC-009, CQ-088)
```

Exactly two cross-domain calls are legal (ARC-016 – ARC-019):
`auth.service → simulation.service.claim_for_user()` and
`documents.service → applications.service.recompute_status()`. Both go through `service.py`, never
into the other domain's repository.

Work that does **not** belong in a route handler (CQ-019):

| Concern | Home |
|---|---|
| Input validation | pydantic schema |
| Authorisation | dependency |
| Business rules, orchestration | service |
| Domain error → HTTP status | `core/exception_handlers.py` |

If a change requires editing two domains and it is not one of the two declared edges, stop and say
the boundary is wrong (ARC-015). Do not work around it.

## Deciding on a try block

Ask: **can I do something with this exception?**

- Translate a low-level error into a domain error → yes, wrap it (CQ-054).
- Add context, restore state, or return a meaningful fallback → yes (CQ-052, CQ-055).
- The client controls the input and the failure is expected → yes (CQ-056).
- Anything else → let it propagate to the global handler.

Then check the hard rules: no bare `except:`, no `except Exception` without re-raising something more
specific, always `raise ... from exc`, never log and swallow (CQ-058 – CQ-061).

## Gate before you call it done

```
backend:   ruff check .  →  mypy --strict app  →  pytest
frontend:  npx eslint .  →  npx tsc --noEmit   →  npm test
```

Green linter, clean `mypy --strict`, passing tests. Not "it runs" (CQ-079).

Run these yourself; no hook is committed to run them for you. If a tool is not installed yet, say so
explicitly rather than reporting success.

## Self-review — what the machine cannot check

Appendix B of the spec marks these `review`. Walk them explicitly before finishing; nothing else
will catch them.

- [ ] Every route handler is exactly one `return service.x(...)` — no `if`/`for`/`while`/`try`, no
      arithmetic, no repository or calculator call, no second service call (CQ-017, CQ-018)
- [ ] No domain imports another domain's internals; `core` imports nothing from `domains`; only
      `repository.py` touches storage; only `main.py` knows all domains (ARC-011 – ARC-014)
- [ ] No cross-domain call beyond the two declared edges (ARC-016)
- [ ] `calculator.py` / `state_machine.py` / `checklist.py` import only stdlib, `decimal` and their
      own `entities.py`, never SQLAlchemy or a session, and are synchronous (ARC-013, CQ-048)
- [ ] Frontend: components take `@Input`/`@Output` and inject nothing; only `pages/` hold state;
      `shared/` has no domain imports (ARC-022, ARC-023)
- [ ] Every `try` block earns its place; every `except` re-raises with `from exc` (CQ-052, CQ-057 – CQ-060)
- [ ] Functions ≤30 lines, ≤4 positional params, nesting ≤3, no boolean flag parameters
      (CQ-036 – CQ-040)
- [ ] No lambda where a named function works; comprehensions over `map`/`filter` (CQ-041, CQ-042)
- [ ] Docstrings explain *why*; no `"""Return the user."""` noise; every module states what it owns
      (CQ-045, CQ-046)
- [ ] `frozen=True, extra="forbid"` on request and response models (CQ-025, CQ-026)
- [ ] Money is `Decimal` in Python and `string` in TypeScript, serialised as a string, never
      round-tripped through `number` (CQ-014, CQ-027, ARC-026)
- [ ] No `async def` without an `await`; no `time.sleep` or synchronous HTTP client in async code
      (CQ-050)
- [ ] No SQLAlchemy row escapes a repository; no lazy loading outside it (CQ-088, CQ-089)
- [ ] The service commits, not the repository; the session is injected, never created (CQ-090, CQ-091)
- [ ] `select`/`insert`/`update`/`delete` only in `repository.py` (CQ-093)
- [ ] Money columns are `Numeric(12, 2)` and read as `Decimal` (CQ-086)
- [ ] Pure domain logic was written test-first (CQ-070)

Frontend only:

- [ ] Every `*.component.css` is empty; no `@apply` outside `@layer base` (UI-027, UI-028)
- [ ] No hex outside `@theme`, no arbitrary colour or spacing values, no `[ngStyle]` or `style="..."`
      (UI-029 – UI-032)
- [ ] Class order left to `prettier-plugin-tailwindcss`, not hand-ordered (UI-033)
- [ ] PrimeNG only for the four declared components; appearance changed in the preset, never with a
      CSS override (UI-036, UI-037, ARC-037)
- [ ] Focus visible on every control; every input has a `<label for>`; colour never carries meaning
      alone (UI-057 – UI-059)
- [ ] The screen behaves as `4-ux.md` says: no blank first paint, no disappearing previous result,
      errors beside their field (UX-009, UX-013, UX-024)

For a diff you did not write, delegate to the `code-quality-reviewer` agent instead of walking this
by hand.
