# Oper credits — borrower portal

A Belgian mortgage borrower portal: simulate a loan, sign up, fill in and submit an application,
upload the supporting documents it asks for.

**Live:** https://oper-credits-borrower-portal.fly.dev
**Run it:** `make dev` · **Gate:** `make lint && make test`

---

## Scope

The four flows the brief asks for, and where each lives:

| Flow | Route | Notes |
|---|---|---|
| Mortgage simulation | `/calculator` | Public, prefilled, computed on load — no calculate button |
| Sign up | `/signup` | The anonymous simulation is claimed and seeds the application |
| Application | `/applications/:id` | Four-step wizard, saved server-side from step one |
| Documents | same page | Checklist **derived** from the answers, not a fixed list |

Three things beyond scope earned their place:

- **Cash needed on the day**, given equal billing with the monthly payment. Registration duty is
  paid from savings and cannot be financed; on a €300 000 Flemish house, first-home status is
  €30 000 of cash the buyer must have. A simulator that hides that is not simplified.
- **A derived checklist.** An employee needs payslips; a self-employed borrower needs a tax
  assessment and an accountant's statement; a new build needs a permit. The list is a function of
  the answers, and it changes when they do.
- **Affordability as a band**, never a decision — DSTI and *restleefgeld* against representative
  lender norms, with the workings shown.

Optional, behind a flag: **AI document classification**. With `AI_CLASSIFICATION_ENABLED=false` the
borrower types their figures and the product works end to end. That is the base case, not a
fallback.

### What is deliberately not here

No credit scoring, no lender-specific pricing, no CKP consultation, no ESIS sheet, no back-office,
no email, no refresh tokens, no migrations. Each cut is named in the spec rather than left to be
discovered — `SCP-001` … `SCP-024` in [`specs/0-business-logic.md`](specs/0-business-logic.md).

---

## Architecture — an MVP-ready monolith

```
        /\
       /  \        ▄▄▄▄▄▄▄
      /    \      █ ▄▄▄▄▄ █
     /  /\  \     █ █   █ █
    /  /  \  \    █ █▄▄▄█ █
   /__/    \__\   █▄▄▄▄▄▄▄█

        « За Монолит »
```

One deployable artefact, not two (`DEP-001`): Angular builds to static files, FastAPI serves them
from the same container. SQLite on a mounted volume; uploaded blobs on the same volume beside it,
never in the database. Deployed to Fly.io, one machine, Amsterdam.

**Data model** — six tables:

```
users ──< simulations                 anonymous until claimed at signup
users ──< applications ──< borrowers  the collection is replaced wholesale on PATCH
                       ──< documents  bytes on disk, an opaque key on the row
                       ──  application_financials   confirmed figures, with provenance
```

`application_financials` is separate from `borrowers` on purpose: the borrower collection is
replaced wholesale on every PATCH, so anything stored there is destroyed the next time the wizard is
edited. The figures the affordability assessment reads must outlive that.

**Layering** — `router → service → (calculator | state machine | checklist) → repository`, arrows
one way only:

- a **route handler is exactly one statement**, a single call to a service — no `if`, no shaping;
- the **repository is the ORM boundary**: a SQLAlchemy row never reaches a service;
- the **service owns the transaction**, which is what lets one upload write a document and move the
  application status atomically;
- `calculator.py`, `state_machine.py`, `checklist.py`, `affordability.py`, `file_type.py` and the
  classifier's `evaluator.py` are **pure** — stdlib and `Decimal` only, fully synchronous, and
  100% covered;
- exactly **three cross-domain edges** exist and all three are declared in
  [`specs/2-architecture.md`](specs/2-architecture.md) §5.

Money is `Decimal` in Python and **`string` in TypeScript**, serialised as a string over JSON.
Never a float, never a JS `number`.

Observability hooks are in place: structured JSON logs with a request id and redaction by default
(an amount, an email or a filename never reaches a log line), plus OpenTelemetry spans around the
two operations worth measuring. `observability/` has an optional local LGTM stack.

**Roughly:** 6 700 lines of backend, 5 000 of frontend, 20 000 of tests, 7 400 of specification.

---

## Run it

```bash
make dev      # whole stack in Docker, hot reload, http://localhost:4200
```

Or without containers:

```bash
make venv                     # once
make backend                  # :8000
make frontend                 # :4200, proxying /api
```

The gate — the same one every ticket had to pass:

```bash
make lint     # ruff + mypy --strict + eslint + the shell checks no linter expresses
make test     # 407 backend, 33 vitest, 13 Playwright
```

Copy `.env.example` to `.env` if you want the optional classifier; without a key it stays off and
everything else works.

**Clicking through it:** `backend/tests/fixtures/walkthrough/` holds one document per checklist row,
named after the row it belongs in, with a README mapping file → row → expected result. Invented
Belgian documents, coherent figures, every reference number a run of zeroes.

---

## Trade-offs

**1 · Two hours does not buy something both structured and working.** Inside the cap I delivered a
working `/calculator` API and a simple frontend around it. Getting to what is deployed took **6–8
hours of real focused time** over two days. Elapsed time was longer, because I switched between Opus
and Sonnet and waited out token-limit resets. That is the honest number the brief asks for.

**2 · Business logic before implementation.** About 1h30 of the two-hour cap went into `specs/`
before a line of code. Everything after rests on that bet: the argument for this build is "read the
spec", not "read the diff".

**3 · Key business logic, not detailed business logic.** Credit rating, lender-specific pricing and
the rest of the underwriting apparatus are outside the scope and outside my depth — I do not have
firm domain knowledge in Belgian lending, and the spec says so rather than bluffing. What is modelled
is high-level mechanics: regional purchase tax, quotiteit, actuarial rate conversion, JKP, and the
document set a file actually needs.

**4 · A limited budget rules out multi-agent work.** No unlimited Claude or Cursor plan, so despite
the spec-driven setup there was no multi-agent fan-out: one ticket at a time, each with its input,
prompt and result checked by hand. The honest other half — there was no time to read every commit
closely. I read the simulation service and the backend entities properly; the frontend I reviewed
for folder structure and general readability and little else.

**5 · Personal credentials are required in the form but semi-mandatory in substance.** Identity and
bank statements are required checklist rows, and any valid PDF satisfies them — acceptance is by
magic bytes, not by content. I did not adopt EU GDPR as a governing constraint, because this is not
a real application handling real data, and I would rather write that down than leave it implied.
What I did hold to: **nothing is extracted from an identity document or a bank statement**. A
national register number is a materially different commitment from a salary figure, and declining
to read it is a stronger position than reading it because we could.

**6 · The 2-hour cap, answered directly.** Most of it went into the specifications, the code rules
and the Claude setup in `.claude/`. That is the core, and everything after it did not fit — which I
assume is the expected outcome. With an unlimited Opus 5 plan I am fairly confident the same result
would have landed in 4–5 hours.

---

## The AI workflow

Claude Code throughout. **Opus 5** for the specifications, **Opus 5 on the provided key** for the
implementation, and roughly 50/50 Opus 5 and Sonnet 5 for everything else.

The work was cut into tickets in [`specs/10-implementation.md`](specs/10-implementation.md) and run
in **seven batches**, one `/plan` prompt per batch, each merged with `--no-ff` so the history reads
the way the plan did — `git log --merges` shows the shape. 109 commits. The gate ran per ticket,
not per batch: nothing merged with a failing lint or a failing `mypy --strict`.

The setup is in the repo rather than described:

| Path | What it does |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | The hard rules, loaded every session |
| [`.claude/hooks/`](.claude/hooks) | **PostToolUse hooks**: ruff + mypy on Python, eslint on the frontend, after *every* write |
| [`.claude/settings.json`](.claude/settings.json) | Hook wiring and the tool allow-list |
| [`.claude/agents/`](.claude/agents) | A reviewer agent for the rules no linter expresses |
| [`.claude/commands/`](.claude/commands) | The per-ticket implement command |
| [`.claude/skills/`](.claude/skills) | The code-quality skill |

The hooks are the part I would point at: the agent is constrained **mechanically**, not by being
asked nicely. A write that breaks typing fails before the next tool call.

One surprise worth recording: **Opus 5 spent the USD 75 budget in about an hour.** I did not expect
it to be that expensive, and it shaped every decision after it.

### Where I did not trust the model

**The business rules are mine.** The calculation engine was specified to the cent before any code
existed, and pinned by acceptance criteria `AC-001` – `AC-009` — a published KBC example reproduced
to €1152.95, the actuarial rate conversion that is *not* `I/12`, the six-row regional tax matrix,
and a schedule that closes at exactly `0.00`. Every ticket was bounded by its test cases first.

**The model advises; deterministic code decides.** Not a claim — a structure:

- [`documents/classification/evaluator.py`](backend/app/domains/documents/classification/evaluator.py)
  is a pure decision table. It takes a parsed verdict and returns one of five outcomes. No network,
  no session, no model call — every row is testable offline.
- [`classification/pipeline.py`](backend/app/domains/documents/classification/pipeline.py) keeps
  extracted figures **only** when classification confirms the type the borrower declared. Numbers
  read off a document that turned out to be something else describe the wrong document.
- No outcome ever reassigns `doc_type`, satisfies a checklist row, or moves an application. The
  worst a wrong answer can produce is an unhelpful hint.
- A figure read from a document is a **proposal** until the borrower confirms it (`DOM-030`), and
  [`applications/affordability.py`](backend/app/domains/applications/affordability.py) returns a
  **band, never a decision** — nothing in the state machine reads it.

With the flag off, none of this exists and the product still works. That was the test of the design.

---

## What I changed from the reference

- **Cash needed on the day is a headline figure**, not a detail — see above.
- **The checklist is derived**, not fixed. A static list is a design error rather than a
  simplification, and it is a large part of why mortgage files arrive incomplete.
- **The simulator opens with a result.** Prefilled and computed on first paint, no calculate button,
  and the previous result stays on screen while a new one loads.

## Honest gaps

Two write-ups, neither of them flattering, both in the repo:

- [`docs/sessions/p4-review.md`](docs/sessions/p4-review.md) — the validation pass. Twelve defects,
  including one that made the **deployed application unusable** while 400 tests passed, because no
  test exercised the artefact that ships.
- [`docs/sessions/spec-conformance.md`](docs/sessions/spec-conformance.md) — an audit of 673
  requirement ids against the code. No critical divergence; three things declared and not delivered,
  all in the optional classifier, one of them user-visible.

## Specs

[`specs/README.md`](specs/README.md) explains the conventions. In short: `0-business-logic.md` is the
domain and wins over everything; `1-code-quality.md` is how code is written and `2-architecture.md`
where it lives; `3-ui.md` and `4-ux.md` split appearance from behaviour; `5-deployment.md`,
`6-auth.md`, `7-validation.md`, `8-api.md`, `9-ai-classification.md` and `10-implementation.md`
cover the rest. Requirements carry stable ids and are superseded in place, never renumbered.
