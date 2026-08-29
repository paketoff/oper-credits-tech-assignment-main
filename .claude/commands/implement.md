---
description: Implement a task against the specs, then run the full quality gate
---

Implement: $ARGUMENTS

Follow this order. Do not skip step 1 — it is what keeps the specs the source of truth.

## 1. Ground the work in the specs

- Read the sections of [`specs/0-business-logic.md`](../../specs/0-business-logic.md) that govern
  this task and list the business requirement IDs (`SIM-`, `DOM-`, `DOC-`, `APP-`, `ERR-`, `AC-`).
- Read [`specs/2-architecture.md`](../../specs/2-architecture.md) §2 – §5 to place the code: the
  tree, what each file owns, the dependency direction, and the two legal cross-domain edges. List the
  `ARC-` ids that constrain it.
- Read the sections of [`specs/1-code-quality.md`](../../specs/1-code-quality.md) that govern how you
  write it, and list the `CQ-` ids. At minimum §3 (the controller rule).
- **Frontend tasks**: read [`specs/3-ui.md`](../../specs/3-ui.md) §5 for the styling rules and the
  component recipe for what you are building, and [`specs/4-ux.md`](../../specs/4-ux.md) for the
  behaviour of that screen. List the `UI-` and `UX-` ids.
- State both lists before writing any code. If the two specs disagree, the business spec wins.
- If the task is not covered by a spec, say so and ask whether to extend the spec first.

## 2. Test-first where it matters

Pure domain logic — calculator, state machine, checklist generator — is written test-first (CQ-070).
The acceptance criteria `AC-001` – `AC-008` in `0-business-logic.md` §20 are the test suite, not a
suggestion (CQ-075). Naming: `test_<subject>_<condition>_<expectation>` (CQ-072).

Everything else gets tests after the fact, and only a few (CQ-071).

## 3. Implement

Place code by the tree in `2-architecture.md` §2. Respect the import boundaries (ARC-011 – ARC-014).
If the change requires a cross-domain call beyond the two declared in ARC-017 and ARC-018, stop and
report that the boundary is wrong (ARC-015).

## 4. Gate

```
backend:   ruff check .  &&  mypy --strict app  &&  pytest
frontend:  npx eslint .  &&  npx tsc --noEmit   &&  npm test
```

Run whichever applies. Green linter, clean `mypy --strict`, passing tests — not "it runs" (CQ-079).
If a tool is not installed yet, say so explicitly rather than reporting success.

## 5. Review what the machine cannot check

Walk the self-review checklist in [`.claude/skills/code-quality`](../skills/code-quality/SKILL.md),
or delegate to the `code-quality-reviewer` agent. Appendix B of the code-quality spec lists exactly
which rules are `review`-only — those are the ones that need your attention here.

## 6. Report

State what you implemented, which requirement IDs it satisfies, what the gate returned verbatim, and
anything you deliberately left out.
