---
name: code-quality
description: Apply this project's code-quality rules (specs/1-code-quality.md, CQ-001..CQ-079) when writing or editing any Python under backend/ or any TypeScript/Angular under frontend/. Use when implementing a domain, adding a route, service, calculator, repository, pydantic schema, Angular component or service, writing tests, or reviewing a diff in this repo. Covers layering and the controller rule, import boundaries, typing, function limits, error handling, docstrings, async, and persistence.
---

# Code quality — how to apply the rules

The rules live in [`specs/1-code-quality.md`](../../../specs/1-code-quality.md). This file is the
procedure, not a second copy of them — referencing by `CQ-` id keeps one source of truth.

## Before writing code

1. **Identify what you are touching**: a domain (`simulation`, `applications`, `documents`, `auth`),
   `core/`, or the frontend.
2. **Read the governing sections** of `specs/1-code-quality.md` for that area. At minimum §2
   (structure and import rules) and §3 (layering) — those decide *where* code goes, and are
   expensive to fix afterwards.
3. **Read the business spec** for any rule that overrides: `specs/0-business-logic.md`. It wins on
   every disagreement.
4. **Name the requirement IDs** you are implementing, business (`SIM-`, `DOM-`, …) and code (`CQ-`).

## Where code goes

```
router.py      routes only — one statement per handler (CQ-017)
service.py     business logic, orchestration
calculator.py  pure functions, no IO, synchronous (CQ-007, CQ-048)
state_machine.py  pure — owns the allowed transitions (APP-009)
checklist.py   pure — derives the required document set (DOC-005)
schemas.py     pydantic request/response models
repository.py  the only code that touches storage (CQ-008)
```

Work that does **not** belong in a route handler (CQ-019):

| Concern | Home |
|---|---|
| Input validation | pydantic schema |
| Authorisation | dependency |
| Business rules, orchestration | service |
| Domain error → HTTP status | `core/exception_handlers.py` |

If a change requires editing two domains, stop and say the boundary is wrong (CQ-009). Do not work
around it.

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
      `repository.py` touches storage (CQ-005, CQ-006, CQ-008)
- [ ] `calculator.py` / `state_machine.py` / `checklist.py` import nothing from the framework, the
      repository or the config, and are synchronous (CQ-007, CQ-048)
- [ ] Every `try` block earns its place; every `except` re-raises with `from exc` (CQ-052, CQ-057 – CQ-060)
- [ ] Functions ≤30 lines, ≤4 positional params, nesting ≤3, no boolean flag parameters
      (CQ-036 – CQ-040)
- [ ] No lambda where a named function works; comprehensions over `map`/`filter` (CQ-041, CQ-042)
- [ ] Docstrings explain *why*; no `"""Return the user."""` noise; every module states what it owns
      (CQ-045, CQ-046)
- [ ] `frozen=True, extra="forbid"` on request and response models (CQ-025, CQ-026)
- [ ] Money is `Decimal` in Python and `string` in TypeScript, serialised as a string (CQ-014, CQ-027)
- [ ] No `async def` without an `await`; no `time.sleep` or synchronous HTTP client in async code
      (CQ-050)
- [ ] Writes are atomic via `os.replace`; repositories return domain models, never dicts
      (CQ-065, CQ-067)
- [ ] Pure domain logic was written test-first (CQ-070)

For a diff you did not write, delegate to the `code-quality-reviewer` agent instead of walking this
by hand.
