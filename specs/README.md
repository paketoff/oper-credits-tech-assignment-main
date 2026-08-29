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

Specs are numbered in reading order. `0-business-logic.md` is the root spec; later
specs build on it and do not restate it. Numbering is reserved ahead of writing so the
sequence never has to be renumbered:

```
0-business-logic.md   written
1-code-quality.md     written
2-architecture.md     written
3-ui.md               written
4-ux.md               written
5-deployment.md       reserved
6-auth.md             reserved
7-validation.md       reserved — referenced by 4-ux.md §4
```

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

IDs attach to verifiable statements only: an invariant, a formula, a constant, a
transition, an error code. Narrative framing stays unlabelled prose. IDs are stable
once published — supersede, never renumber.

## Enforcement

A spec no agent reads is decoration. The rules reach the code through four layers:

| Layer | Fires |
|---|---|
| `CLAUDE.md` | always — loaded into context every session |
| `specs/*.md` | when read |
| `.claude/skills/code-quality`, `.claude/commands/implement.md`, `.claude/agents/code-quality-reviewer.md` | on implementation and review work |
| `pre-commit` and CI | deterministically, on every change — the binding gate |

`1-code-quality.md` Appendix B records which rules a machine proves and which only review
catches.
