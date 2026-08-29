# Specs

Specifications are the source of truth for this project. Behaviour is described
here first, then implemented. Any change in system behaviour starts with a change
to a spec.

## Layout

| File | Purpose |
|---|---|
| `business-logic.md` | Domain model and business rules (root spec) |

## Conventions

- One file per coherent area. When a file grows too large, split it into
  `specs/<domain>/`.
- Every requirement carries a stable ID (`BL-001`, `API-014`, ...) so code, tests
  and commit messages can reference it.
- Spec lifecycle: `draft` → `approved` → `implemented` → `deprecated`.
- Front matter (`id`, `title`, `status`, `version`, `owner`, `updated`) is
  mandatory in every spec file.
