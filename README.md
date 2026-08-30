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
| Documents | same page | The checklist is built from the answers, not a fixed list |

Three things beyond that scope earned their place:

- **The cash you need on the day.** Most simulators show the monthly payment and stop there. But
  the purchase tax, the notary and the registration fees are paid up front, out of savings, and
  cannot be added to the loan. On a €300 000 house in Flanders they come to **€13 175** if it is
  your only home and **€43 175** if it is not — before the deposit. That number decides whether
  someone can buy at all, so it sits beside the monthly payment instead of in a footnote.
- **A checklist that follows the answers.** An employee is asked for payslips; a self-employed
  borrower for a tax assessment and an accountant's statement; a new build for a permit. Change the
  answer and the list changes with it. A fixed list is a large part of why mortgage files arrive
  incomplete.
- **An affordability read.** How much of the household's income the loan would take, and what would
  be left each month, against the norms Belgian lenders commonly apply. It is a reading, never an
  approval or a refusal.

Optional, behind a flag: **AI document classification**. Switched off, the borrower types their
figures in and everything works. That is the normal case, not a fallback.

### What is deliberately not here

No credit scoring, no lender-specific pricing, no back-office, no email, no database migrations.
Each cut is written down in the spec rather than left to be discovered — `SCP-001` … `SCP-024` in
[`specs/0-business-logic.md`](specs/0-business-logic.md).

---

## Architecture

**A monolith, deliberately, and one that is ready to deploy.** Angular is built into static files
that FastAPI serves; the database and the uploaded files sit on one mounted volume beside it. One
artefact, one container, one machine on Fly.io. For an application this size, two services would be
overhead without a payoff.

**Organised by domain, with room to grow.** The folders are `simulation`, `applications`,
`documents` and `auth` — the things the business talks about — rather than `controllers`, `models`
and `services`. Each domain owns its own routes, its own rules and its own storage, and they reach
each other only through a small, written-down set of calls. That is what keeps the monolith from
becoming a knot: pulling a domain out into its own service later is a move, not a rewrite. The same
holds for the pieces underneath — swapping SQLite for Postgres, or local disk for S3, changes one
file each.

**Money is `Decimal` in Python and a `string` in TypeScript**, and crosses the wire as a string.
Never a float, never a JavaScript `number`. This is a product judged on cents, and `0.1 + 0.2` is
the reason.

**Observability is wired in, not bolted on.** Structured JSON logs carrying a request id, with
redaction on by default — an amount, an email or a filename never reaches a log line — and
OpenTelemetry spans around the operations worth measuring. `observability/` holds an optional local
Grafana stack.

---

## Run it

```bash
make dev      # the whole stack in Docker, hot reload, http://localhost:4200
```

Or without containers:

```bash
make venv                     # once
make backend                  # :8000
make frontend                 # :4200
```

The checks — the same ones every ticket had to pass:

```bash
make lint     # ruff, mypy --strict, eslint, and the rules no linter expresses
make test     # 407 backend, 33 frontend, 13 browser
```

Copy `.env.example` to `.env` if you want the optional classifier. Without a key it stays off and
everything else works.

**To click through it:** `backend/tests/fixtures/walkthrough/` has one document per checklist row,
named after the row it belongs in, with a table mapping file → row → what should happen. Invented
Belgian documents, figures that hang together, every reference number a row of zeroes.

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
firm domain knowledge in Belgian lending, and the spec says so rather than bluffing. What is
modelled is the high-level mechanics: regional purchase tax, the loan-to-value ratio, the real
monthly rate, the all-in annual cost, and the documents a file actually needs.

**4 · A limited budget rules out multi-agent work.** No unlimited Claude or Cursor plan, so despite
the spec-driven setup there was no multi-agent fan-out: one ticket at a time, each with its input,
prompt and result checked by hand. The honest other half — there was no time to read every commit
closely. I read the simulation service and the backend entities properly; the frontend I reviewed
for folder structure and general readability and little else.

**5 · Personal credentials are required in the form but semi-mandatory in substance.** Identity and
bank statements are required rows on the checklist, and any valid PDF satisfies them — a file is
accepted on what its bytes say it is, not on what is written inside. I did not adopt EU GDPR as a
governing constraint, because this is not a real application handling real data, and I would rather
write that down than leave it implied. What I did hold to: **nothing is read out of an identity
document or a bank statement**. A national register number is a materially different commitment
from a salary figure, and declining to read it is a stronger position than reading it because we
could.

**6 · The 2-hour cap, answered directly.** Most of it went into the specifications, the code rules
and the Claude setup in `.claude/`. That is the core, and everything after it did not fit — which I
assume is the expected outcome. With an unlimited Opus 5 plan I am fairly confident the same result
would have landed in 4–5 hours.

---

## The AI workflow

Claude Code throughout. **Opus 5** for the specifications, **Opus 5 on the provided key** for the
implementation, and roughly 50/50 Opus 5 and Sonnet 5 for everything else.

The work was cut into tickets in [`specs/10-implementation.md`](specs/10-implementation.md) and run
in **seven batches**, one `/plan` prompt per batch, each merged separately so the history reads the
way the plan did — `git log --merges` shows the shape. 109 commits. The checks ran per ticket, not
per batch: nothing merged with a failing lint or a failing type check.

The setup is in the repo rather than described:

| Path | What it does |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | The hard rules, loaded every session |
| [`.claude/hooks/`](.claude/hooks) | Runs the linters and the type checker after *every* file the agent writes |
| [`.claude/settings.json`](.claude/settings.json) | Hook wiring and the tool allow-list |
| [`.claude/agents/`](.claude/agents) | A reviewer agent for the rules no linter can express |
| [`.claude/commands/`](.claude/commands) | The per-ticket implement command |
| [`.claude/skills/`](.claude/skills) | The code-quality skill |

The hooks are the part I would point at: the agent is constrained **mechanically**, not by being
asked nicely. A write that breaks typing fails before the next step runs.

One surprise worth recording: **Opus 5 spent the USD 75 budget in about an hour.** I did not expect
it to be that expensive, and it shaped every decision after it.

### Where I did not trust the model

**The business rules are mine.** The calculation was specified to the cent before any code existed,
and pinned by nine acceptance criteria — a published KBC example reproduced to €1152.95, the rate
conversion that is *not* simply the annual rate divided by twelve, the six-row regional tax matrix,
and a repayment schedule that closes at exactly zero. Every ticket was bounded by its test cases
first.

**The model advises; ordinary code decides.** Not a claim — a structure:

- The module that decides what a classification *means*
  ([`evaluator.py`](backend/app/domains/documents/classification/evaluator.py)) takes the model's
  answer and returns one of five outcomes. No network, no database — every case is testable
  offline.
- Figures read from a document are kept **only** when the model agreed the document is what the
  borrower said it was ([`pipeline.py`](backend/app/domains/documents/classification/pipeline.py)).
  Numbers read off the wrong document describe the wrong document.
- No outcome ever changes a document's type, ticks a checklist row, or moves an application
  forward. The worst a wrong answer can produce is an unhelpful hint.
- A figure read from a document is a **suggestion** until the borrower confirms it, and the
  affordability module returns a **reading, never a decision** — nothing in the application's
  lifecycle reads it.

Switch the flag off and none of this exists, and the product still works. That was the test of the
design.

---

## What I changed from the reference

- **The cash needed on the day is a headline figure**, not a detail — see above.
- **The checklist is built from the answers**, not fixed.
- **The simulator opens with a result.** Prefilled and computed on the first paint, no calculate
  button, and the previous result stays on screen while a new one loads.

## Honest gaps

Two write-ups, neither flattering, both in the repo:

- [`docs/sessions/p4-review.md`](docs/sessions/p4-review.md) — the validation pass. Twelve defects,
  including one that made the **deployed application unusable** while 400 tests passed, because no
  test exercised the thing that actually ships.
- [`docs/sessions/spec-conformance.md`](docs/sessions/spec-conformance.md) — an audit of 673
  written requirements against the code. Nothing critical diverges; three things were declared and
  not delivered, all in the optional classifier.

## Specs

[`specs/README.md`](specs/README.md) explains the conventions. In short: `0-business-logic.md` is
the domain and wins over everything else; `1-code-quality.md` is how code is written and
`2-architecture.md` where it lives; `3-ui.md` and `4-ux.md` split what it looks like from how it
behaves; `5-deployment.md`, `6-auth.md`, `7-validation.md`, `8-api.md`, `9-ai-classification.md`
and `10-implementation.md` cover the rest. Requirements carry stable ids and are corrected in
place, never renumbered.
