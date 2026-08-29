# Specs

Specifications are the source of truth for this project. Behaviour is described
here first, then implemented. Any change in system behaviour starts with a change
to a spec.

## Layout

| File | Purpose |
|---|---|
| `0-business-logic.md` | Scope, domain model and simulation engine — the whole business domain |
| `1-code-quality.md` | Typing, error handling, style — how code is written |
| `2-architecture.md` | Folder tree, import boundaries, layering, naming — where code lives |
| `3-ui.md` | Colour, type, Tailwind, PrimeNG, components — what the frontend looks like |
| `4-ux.md` | Flows, states, timing, empty and error behaviour — how it behaves |
| `5-deployment.md` | Container, hosting, volume, logging, tracing, metrics — how it runs |
| `6-auth.md` | Passwords, session cookie, authorisation, rate limiting — who may do what |
| `7-validation.md` | Validation rules, the error registry, 57 edge cases, the manual test plan |

Specs are numbered in reading order. `0-business-logic.md` is the root spec; later
specs build on it and do not restate it. The eight specs:

```
0-business-logic.md   1-code-quality.md   2-architecture.md   3-ui.md
4-ux.md               5-deployment.md     6-auth.md           7-validation.md
```

The set is complete. A new spec takes the next number and declares its own namespace.

**Precedence: where a spec and `0-business-logic.md` disagree, the business spec wins.** Between
the other two, `2-architecture.md` is canonical for structure and import boundaries;
`1-code-quality.md` keeps the ids that moved there as one-line pointers.

## Conventions

- One file per coherent area. When a file grows too large, split it into
  `specs/<domain>/`.
- Every requirement carries a stable ID so code, tests and commit messages can
  reference it.
- Every rule is stated **once**, at one canonical section. Other mentions carry a
  one-line statement plus a `→ §N` pointer, never a second copy of the rule.
- Spec lifecycle: `draft` → `approved` → `implemented` → `deprecated`.
- Front matter (`id`, `title`, `status`, `version`, `owner`, `updated`) is
  mandatory in every spec file.
- Each spec ends with a traceability appendix mapping every ID to its source and
  section.

## ID namespaces

| Prefix | Covers |
|---|---|
| `SCP-` | Scope boundaries, cuts, simplifications, definition of done |
| `DOM-` | Money rules, entities, invariants, ownership |
| `DOC-` | Document types, upload limits, checklist derivation |
| `APP-` | Application lifecycle states and transitions |
| `SIM-` | Calculation rules, formulas and constants |
| `ERR-` | Error codes and HTTP mapping |
| `AC-` | Acceptance criteria — each maps to a test |
| `CQ-` | Code quality — typing, error handling, style (`1-code-quality.md`) |
| `ARC-` | Architecture — structure, imports, layering, naming (`2-architecture.md`) |
| `UI-` | Visual system — tokens, type, styling rules, components (`3-ui.md`) |
| `UX-` | Behaviour — flows, timing, states (`4-ux.md`) |
| `DEP-` | Deployment and observability (`5-deployment.md`) |
| `AUTH-` | Auth and security (`6-auth.md`) |
| `VAL-` | Validation, error registry, edge cases (`7-validation.md`) |

IDs attach to verifiable statements only: an invariant, a formula, a constant, a
transition, an error code. Narrative framing stays unlabelled prose. IDs are stable
once published — supersede, never renumber.

Two consequences of that rule:

- **New ids are allocated next-free, not by position.** Once a spec is published, a rule
  added to an early section takes the next unused number rather than pushing everything
  down. Ids identify, they do not order.
- **A rule that stops being true is withdrawn, not deleted.** It keeps its id, its original
  wording, and a line saying what superseded it, so a reference from an older commit still
  resolves. See `1-code-quality.md` §11.5.

## Enforcement

A spec no agent reads is decoration. The rules reach the code through four layers:

| Layer | Fires |
|---|---|
| `CLAUDE.md` | always — loaded into context every session |
| `specs/*.md` | when read |
| `.claude/skills/code-quality`, `.claude/commands/implement.md`, `.claude/agents/code-quality-reviewer.md` | on implementation and review work |
| `make lint` and `make test` | the binding gate, run before a unit of work is called done |

`1-code-quality.md` Appendix B records which rules a machine proves and which only review
catches.
