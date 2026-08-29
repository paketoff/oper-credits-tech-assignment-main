# Specs

Specifications are the source of truth for this project. Behaviour is described
here first, then implemented. Any change in system behaviour starts with a change
to a spec.

## Layout

| File | Purpose |
|---|---|
| `0-business-logic.md` | Scope, domain model and simulation engine — the whole business domain |

Specs are numbered in reading order. `0-business-logic.md` is the root spec; later
specs (architecture, API, infrastructure) build on it and do not restate it.

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

IDs attach to verifiable statements only: an invariant, a formula, a constant, a
transition, an error code. Narrative framing stays unlabelled prose. IDs are stable
once published — supersede, never renumber.
