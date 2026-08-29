# Session logs

Agent session logs, one file per unit of work, organised by phase (`10-implementation.md` T05, T41).

They start at T01 rather than being reconstructed at the end, because they cannot be reconstructed at
the end. Part C of the assignment is twenty minutes of walking through how the work was actually
done, and a log written afterwards is a story about the work rather than a record of it.

## Layout

```
docs/sessions/
  p0-skeleton/      T01 – T05, T43
  p1-domain-core/   T06 – T12
  p1-platform/      T13 – T16, T44
  p2-api/           T17 – T25
  p3-frontend/      T26 – T30
  p4-integration/   T31 – T34
  p5-classification/ T35 – T38
  p6-ship/          T39 – T42
```

## What is worth keeping

Not the transcript. The reviewer will sample these, not read them line by line, so each file opens
with two lines saying what happened and what it cost.

The entries that earn their place are the ones where the output was **wrong and was corrected** —
T42 asks for one concrete moment where the specification or the generated code was not trusted and
was rewritten. Those moments are the argument that the process is real. So far:

| Phase | Moment |
|---|---|
| p0 | `mypy --strict` with `disallow_any_explicit` rejects every pydantic model, so `CQ-023` and `CQ-024` could not both hold. The flag was dropped and `ANN401` took the rule over (T02). |
| p0 | The `UI-027` lint check ran, matched nothing, and passed — its glob assumed a filename Angular 22 no longer generates. It was passing on an empty set (T43). |
| p0 | The dev compose service built a stage where `uvicorn` is not on `PATH`; `make dev` could never have started (T43). |
| p0 | `infra/.dockerignore` is never read — Docker looks at the *context* root. It would have shipped `node_modules` into the build context and said nothing (T03). |
| p1 | **`AC-003`'s totals were wrong.** `424355.98` is the unrounded payment times the term; no schedule produces it, and it contradicted `SIM-008`. Three candidates existed and only one satisfies all the invariants at once (T07). |
| p1 | `T-P5`'s Tier 1 coverage command used file paths. Coverage collected nothing and reported 0% — a gate that cannot pass, whose obvious "fix" is to lower the threshold (T10). |
| p1 | `ARC-013` forbade pure modules from importing `core/errors.py`, while `CQ-054` and `VAL-004` required them to raise domain errors. The spec asked for something it also banned (T06). |
| p1 | `ruff` B015 caught a test asserting nothing: `assert_transition(...) is None` with no `assert`. The linter found a real defect, not a style issue (T11). |
