---
description: Implement a task against the specs, then run the full quality gate
---

Implement: $ARGUMENTS

Follow this order. Do not skip step 1 — it is what keeps the specs the source of truth.

## 1. Ground the work in the specs

- Read the sections of [`specs/0-business-logic.md`](../../specs/0-business-logic.md) that govern
  this task and list the business requirement IDs (`SIM-`, `DOM-`, `DOC-`, `APP-`, `ERR-`, `AC-`).
- Read the sections of [`specs/1-code-quality.md`](../../specs/1-code-quality.md) that govern the
  code you are about to write, and list the `CQ-` ids that constrain it. At minimum §2 (structure,
  import rules) and §3 (layering, the controller rule).
- State both lists before writing any code. If the two specs disagree, the business spec wins.
- If the task is not covered by a spec, say so and ask whether to extend the spec first.

## 2. Test-first where it matters

Pure domain logic — calculator, state machine, checklist generator — is written test-first (CQ-070).
The acceptance criteria `AC-001` – `AC-008` in `0-business-logic.md` §20 are the test suite, not a
suggestion (CQ-075). Naming: `test_<subject>_<condition>_<expectation>` (CQ-072).

Everything else gets tests after the fact, and only a few (CQ-071).

## 3. Implement

Place code by the structure in §2 of the code-quality spec. Respect the import boundaries. If the
change requires editing two domains, stop and report that the boundary is wrong (CQ-009).

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
