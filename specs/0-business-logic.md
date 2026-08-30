---
id: BL
title: Business Logic
status: draft
version: 1.0.0
owner: paketoff
updated: 2026-08-29
---

# 0 — Business Logic

Single source of truth for the domain. This document is the merge of three working notes
(`00-scope.md`, `01-domain.md`, `02-simulation.md`) and supersedes all three; they are no longer
maintained.

It defines what is built, the entities and their invariants, the application lifecycle, and the
calculation engine to the cent. It does **not** cover layering, project structure or code style;
those live in a separate spec.

Two rules govern everything below.

**DOM-001 — Derived data is computed, never stored as input.** Loan amount, quotiteit, monthly
payment, JKP, the upfront cost breakdown and the document checklist are all functions of stored
fields. Storing them invites drift between what was saved and what the rules say.

**DOM-002 — Domain rules live in the domain, not in the API layer or the form.** A rule expressed
only as frontend validation does not exist.

Requirement IDs (`SCP-`, `DOM-`, `DOC-`, `APP-`, `SIM-`, `ERR-`, `AC-`) are stable and may be
referenced from code, tests and commit messages. Every rule is stated once, at one canonical
section; other mentions carry a one-line statement and a `→ §N` pointer. Appendix A maps every ID
to its source and section.

---

# Part I — Scope & Context

## 1. What we are building

A **borrower portal**: the public-facing front door of a Belgian mortgage lender. It is the part of
the system a person touches before they are a customer, and it does two jobs at once.

For the borrower, it answers the only question they actually have — *can I afford this house, and
how much money do I need in my account on the day of signing?* — and then collects everything the
lender needs in order to say yes.

For the lender, it is the top of the origination funnel. Its job is to get a complete, correct file
into the credit analyst's hands. In Belgian mortgage origination this is the dominant failure mode:
most files arrive incomplete, get sent back, and take weeks of manual chasing. Every design decision
in this portal is aimed at that problem.

### 1.1 Scope, in one sentence

**SCP-001.** The simulator computes the monthly payment, total cost and full upfront cash
requirement for a residential purchase in Flanders, Wallonia or Brussels, with a fixed rate and
annuity repayment; the application captures the borrower file and collects a document checklist
derived from that file.

### 1.2 The four flows

Four flows, in order:

1. **SCP-002 — Simulate.** Anonymous. No account, no commitment. The borrower enters a price, what
   they can put in themselves, a term and a rate, and gets back a monthly payment plus the full
   amount of cash they need up front. The upfront number is the one that surprises people, and the
   one most simulators either get wrong or hide. → Part III
2. **SCP-003 — Sign up.** An account. The simulation they were just looking at follows them into
   it. → §10
3. **SCP-004 — Apply.** A multi-step form capturing the borrowers, the property, and the loan they
   want. → §9.4
4. **SCP-005 — Upload documents.** Against a checklist *derived from their specific situation*, not
   a fixed list. → §11

## 2. Why this is not a CRUD app

Three things make it a domain problem rather than four tables and a form.

**The arithmetic is legally specified and counter-intuitive.** Belgian mortgage interest is computed
from a monthly periodic rate derived from the annual rate *actuarially*, not by dividing by twelve.
Almost every mortgage calculator on the internet uses division, and almost all of them would be
wrong here. Getting this right is the difference between output a Belgian lender recognises and
output they do not. → §14

**The cost of buying is not the price of the house.** Purchase tax is regional, depends on whether
this is the buyer's only home, is paid from the buyer's own savings, and cannot be financed. → §17

**The required document set is a function, not a list.** An employee needs payslips; a self-employed
borrower needs tax assessments and an accountant's statement. An existing home needs an energy
certificate; a new build needs a building permit and construction quotes. A static checklist is a
large part of why files arrive incomplete. → §11

## 3. What the reviewer is scoring

Stated in the brief, and it drives priority: does the core flow run without them debugging it; is
the code readable, structured and easy to extend; is Python and FastAPI usage idiomatic with
sensible typing and async where it matters; are API design, error handling and data modelling sane;
are there observability hooks; is the code testable. Also: what was cut, and how the two-hour cap
was handled.

Architecture beats features. A clean small app beats a feature-rich mess. A few meaningful tests
beat a sea of generated ones. **Nothing in this spec is worth trading against the core flow
working.**

## 4. Belgian market context that shapes the design

These are facts the code has to encode, not background reading. Each points at the section where it
is stated normatively.

**Interest convention.** For mortgage credit with immovable destination, the annual debit rate `I`
and the monthly periodic rate `i` satisfy `(1 + i)^12 = (1 + I)`. The annual rate is a derived,
informational figure; the periodic rate is what actually applies to the outstanding balance. Belgian
*consumer* credit uses simple division, which is why the wrong convention is easy to reach for.
→ §14

**Quotiteit (loan to value).** The Belgian supervisory norm is 90% of property value. It is a
supervisory expectation, not a statutory cap. Above-90% loans are *flagged*, never rejected. → §9.2

**Registratierechten (purchase tax).** Regional, and dependent on `enige eigen woning` (only own
home) status. Flanders and Wallonia apply a reduced rate to first-home buyers; Brussels instead
applies an *abattement*, an allowance on the first slice of the price rather than a reduced rate —
a different mechanism, modelled differently. → §17.1

**JKP / TAEG.** The lender must disclose the all-in annual cost alongside the nominal rate. It
legally includes the file fee, the valuation fee, the notarial cost of registering the mortgage, and
insurance premiums where the lender requires the policy be taken with them. It excludes the purchase
tax and the purchase-deed notary fee, which are costs of buying a house rather than costs of credit.
→ §18

**Document set.** Conditional on employment type, property type and existing credit. Requirements
are satisfied per document type, not per file. → §11

**Application lifecycle.** Not linear. A file moves back from complete to pending whenever a
document is removed or fails verification. Real lenders additionally gate on property valuation, a
legally mandatory consultation of the central credit register (CKP), and a credit assessment before
issuing a binding offer accompanied by a standardised ESIS information sheet. → §12

## 5. Deliberately not built

Each of these is a real part of the domain. Each is cut for the two-hour cap, not overlooked. The
cut list is part of the deliverable.

**On the cap:** these cuts are scoped against the brief's two-hour limit. The actual work budget is
[`10-implementation.md`](10-implementation.md) §Time budget — roughly five hours across specs and
implementation. That is a stated choice rather than an overrun, and the README carries the real
number; the cuts below stand on their own reasoning regardless.

| ID | Cut | Why, and what it would take |
|---|---|---|
| SCP-006 | Variable rates (1/1/1, 3/3/3, 5/5/5, 10/5/5) | Needs a reset schedule plus two interacting caps: the statutory rule that the rate may at most double relative to its starting value and must be symmetric downward, and the contractual cap, taking whichever favours the borrower. Real work, no extra signal on the core flow. |
| SCP-007 | Repayment types other than annuity | `vaste kapitaalaflossing` (linear), `bullet`, `accordeon` all exist in the market. Annuity is the default. Modelled as an enum with one member so adding the rest is additive, not a migration. → §15 |
| SCP-008 | New-build VAT (21%, or 6% for qualifying demolition-and-rebuild) | A second tax regime that also splits the land share from the construction share. Doubles the tax model for a case the demo does not exercise. |
| SCP-009 | Flemish reductions: 1% for deep energy renovation, €1,867 rebate for modest housing | Conditional rules layered on the base rate, with price thresholds that differ inside and outside the larger cities. Additive later; they do not change the shape of the calculation. |
| SCP-010 | Co-borrowers in the UI | Most Belgian mortgages are joint. The schema keeps `borrowers` as a collection from the start, so this is a form and aggregation problem, not a data-model change. → §9.4 |
| SCP-011 | ~~Affordability assessment (DSTI, `restleefgeld`)~~ — **superseded at T53, now built.** | Was: *"belongs to the application, not the public simulator ... Income is captured; the decision is not computed. First thing to add."* It was the first thing added. Both reasons the cut gave for its shape are kept rather than discarded: it is application-scoped, not part of the public simulator, and it produces an advisory band, never a decision. → §21 |
| SCP-012 | CKP consultation, ESIS issuance, reflection period | Legally mandatory gates. CKP in particular has a 45-day validity window, so it can expire and push a file backwards. Present in the state machine as states; not implemented as integrations. → §12 |
| SCP-013 | Amortisation schedule in the UI | Computed and tested in the backend. Rendering 300 rows costs time and earns nothing. → §16 |
| SCP-014 | Independent property valuation | Appraised value is assumed equal to purchase price. Real lenders use a statistical model and take the lower of the two, which matters because quotiteit is computed against value, not price. → SCP-017 |
| SCP-015 | Field extraction and cross-document checking | The checklist is satisfied by document type **as declared on upload**, and that has not changed. Classification itself is now built — advisory only, behind a flag, in [`9-ai-classification.md`](9-ai-classification.md); it warns, it never decides. Extracting income, dates and account numbers, and cross-checking them between documents, remain cut: they need per-type schemas and a verification story. |

## 6. Simplifications made inside what *is* built

Named here rather than hidden, because an unflagged simplification reads as an error.

- **SCP-016** — The purchase-deed notary fee is a flat constant standing in for a degressive tariff
  set by royal decree. → §17.2
- **SCP-017** — Appraised value equals purchase price. → §9.2, SCP-014
- **SCP-018** — `UNDER_REVIEW` collapses three distinct real-world gates: property valuation, CKP
  consultation and credit assessment. → §12

## 7. Definition of done

- **SCP-019** — A deployed URL where simulate, sign up, apply and upload run end to end with no
  debugging by the reviewer.
- **SCP-020** — The simulator reproduces a published Belgian bank representative example to the
  cent. → AC-001
- **SCP-021** — Purchase tax is correct for all three regions in both first-home and standard
  cases. → AC-004
- **SCP-022** — The document checklist changes when employment type or property type changes.
  → §11
- **SCP-023** — An application can move backwards from complete to pending. → APP-004
- **SCP-024** — Money is `Decimal` everywhere, and the amortisation schedule closes at exactly zero.
  → DOM-003, AC-006

---

# Part II — Domain Model

## 8. Money

**DOM-003.** All monetary values are `Decimal`. Never `float`.

- **DOM-004** — Stored and returned quantised to 2 decimal places, `ROUND_HALF_UP`.
- **DOM-005** — Rates are `Decimal` as fractions, not percentages: 4% is `Decimal("0.04")`.
- **DOM-006** — The monthly periodic rate is carried at full precision internally and only rounded
  for display. Banks quote it at 6 decimal places (`0.373801%`); the schedule must reconcile to the
  cent.

## 9. Entities

### 9.1 Region

**DOM-007.** Enum: `FLANDERS`, `WALLONIA`, `BRUSSELS`. Drives purchase tax only. → §17.1

### 9.2 Simulation

**DOM-008.** Anonymous by default. Created without a session and without a user.

| Field | Type | Note |
|---|---|---|
| `id` | uuid | |
| `user_id` | uuid, nullable | Null until the borrower signs up → §10 |
| `property_value` | Decimal | Purchase price. Assumed equal to appraised value; see SCP-017 |
| `own_contribution` | Decimal | `eigen inbreng` |
| `term_months` | int | |
| `annual_nominal_rate` | Decimal | |
| `region` | Region | |
| `is_first_home` | bool | `enige eigen woning` |
| `created_at` | datetime | |

**DOM-009.** Derived, never stored as input: `loan_amount`, `quotiteit`, `monthly_payment`,
`total_interest`, `total_cost`, `jkp`, and the upfront cost breakdown. Computed by a pure function;
→ Part III.

#### Invariants

- **DOM-010** — `10 000 <= property_value <= 10 000 000`, at 2 decimal places. (Was `> 0`; the
  range comes from `7-validation.md` VAL-008, which also fixes the code `PROPERTY_VALUE_OUT_OF_RANGE`.)
- **DOM-011** — `0 <= own_contribution < property_value`
- **DOM-012** — `loan_amount = property_value - own_contribution`, and `loan_amount > 0`
- **DOM-013** — `12 <= term_months <= 360`
- **DOM-014** — `0 <= annual_nominal_rate <= 0.20`
- **DOM-015** — `quotiteit = loan_amount / property_value`, reported as a fraction

#### Quotiteit and the supervisory norm

**DOM-016.** `quotiteit > 0.90` is **not** a validation error. The Belgian supervisory norm is 90%
of property value, but it is a supervisory expectation, not a statutory cap: Belgium has no
statutory LTV cap, lenders may exceed the norm for a limited share of new production within a
tolerance quota, and the tolerance is wider for first-time buyers. An above-norm loan is returned as
a flag on the response (`above_supervisory_norm`), never rejected. Rejecting it would be wrong.

**DOM-017.** Lenders price in bands by quotiteit, so a larger own contribution buys a lower rate.
The rate is an input to the simulator; band pricing is not modelled.

**DOM-018.** Quotiteit is computed against appraised value, not price. Because appraised value is
assumed equal to purchase price (SCP-017), the two coincide here — which is exactly why SCP-014
matters when independent valuation is added.

### 9.3 User

**DOM-019.** `id`, `email` (unique, case-insensitive), `password_hash`, `created_at`.

**DOM-020.** No real personal data anywhere in this system. Test data only.

### 9.4 Application

| Field | Type | Note |
|---|---|---|
| `id` | uuid | |
| `user_id` | uuid | Owner |
| `simulation_id` | uuid, nullable | The simulation this grew out of |
| `status` | ApplicationStatus | See the state machine, §12 |
| `borrowers` | list | Collection from the start, even though the UI only fills one |
| `property` | object | `region`, `is_first_home`, `property_type` (`EXISTING` / `NEW_BUILD`), `purchase_price` |
| `submitted_at` | datetime, nullable | |
| `created_at` | datetime | |
| `updated_at` | datetime | Touched on every write; surfaced by `8-api.md` §6 |

**DOM-021.** `borrowers` is a collection because most Belgian mortgages are joint. The UI captures
one; the schema does not need changing to capture two. Co-borrowers in the UI are cut (SCP-010) — a
form and aggregation problem, not a data-model change.

**DOM-022. Borrower fields:** `id` (uuid), `full_name`, `date_of_birth`, `employment_type`
(`EMPLOYEE` / `SELF_EMPLOYED` / `OTHER`), `monthly_net_income`, `has_existing_credit`. `borrowers` is
a table of its own (`1-code-quality.md` CQ-085), so each row carries an id; `8-api.md` §6 returns
it.

**DOM-023 (superseded at T53).** Read: *"Income is captured but not yet used for a decision."* It is
now used, but **not from this field** — `borrower.monthly_net_income` is replaced wholesale on every
PATCH (`8-api.md` API-037) and carries no provenance, so it stays what it always was: what the
borrower typed into the wizard. The figure the affordability assessment actually reads lives on the
confirmed financial profile, DOM-029. → §21

**DOM-028.** A borrower is between 18 and 75 years old at submission, computed from
`date_of_birth`. Outside that range the application cannot be submitted — `7-validation.md` VAL-011.

**DOM-024. The first-home flag is a property of the application, not of a borrower.** If any
co-borrower has previously held a mortgage, the status is lost for all of them. Modelling it per
borrower would encode the rule incorrectly.

### 9.5 Document

| Field | Type | Note |
|---|---|---|
| `id` | uuid | |
| `application_id` | uuid | |
| `doc_type` | DocumentType | What requirement it satisfies |
| `filename` | str | Original name, sanitised |
| `storage_key` | str | Opaque; the backend never serves by user-supplied path |
| `content_type` | str | |
| `size_bytes` | int | |
| `uploaded_at` | datetime | |

When the optional classifier is enabled it adds two advisory columns, `classification_status` and
`classification_outcome`, defined in [`9-ai-classification.md`](9-ai-classification.md) §7.1. They
are deliberately not part of this entity: the domain has to stay readable with the feature off.

- **DOC-001** — Accepted content types: `application/pdf`, `image/jpeg`, `image/png`. Anything else
  is rejected with 415. → ERR-003
- **DOC-002** — Size limit 10 MB; over that is 413. → ERR-004
- **DOC-003** — `storage_key` is opaque; the backend never serves by user-supplied path.
- **DOC-004** — `filename` is the original name, sanitised.

## 10. Claiming a simulation

**DOM-025.** A simulation is created anonymously. When the borrower signs up, the simulation they
were looking at is attached to the new user.

- **DOM-026** — The anonymous `id` is held client-side and passed to the signup call.
- **DOM-027** — Attaching sets `user_id` if and only if it is currently null. A simulation already
  owned by another user is never reassigned; the attempt is ignored rather than erroring.

This is the only interesting decision in the data model and is deliberate: forcing signup before
seeing a number is the single biggest source of drop-off in mortgage origination.

## 11. Document checklist

**DOC-005.** The required set is **derived, not stored**. It is a function of the application:

```
required_documents(application) -> list[DocumentRequirement]
```

**DOC-006.** Base, always required:

- `IDENTITY` — identiteitskaart
- `BANK_STATEMENTS` — rekeninguittreksels
- `PURCHASE_AGREEMENT` — compromis

**DOC-007.** Conditional:

| Condition | Adds |
|---|---|
| any borrower `EMPLOYEE` | `PAYSLIPS` (loonfiches), `EMPLOYER_STATEMENT` (werkgeversattest) |
| any borrower `SELF_EMPLOYED` | `TAX_ASSESSMENT` (aanslagbiljet), `ACCOUNTANT_STATEMENT` |
| any borrower `has_existing_credit` | `EXISTING_LOAN_STATEMENTS` |
| `property_type` is `EXISTING` | `EPC` (energieprestatiecertificaat) |
| `property_type` is `NEW_BUILD` | `BUILDING_PERMIT`, `CONSTRUCTION_QUOTE` |

**DOC-011.** `employment_type` of `OTHER` adds **nothing**. It is the honest bucket for a borrower
who is neither employed nor self-employed — a pensioner, a student, someone between jobs — and there
is no single document set that fits all of them. Such a borrower supplies only the three base
requirements, and a credit analyst asks for the rest by hand. The silence is deliberate, not an
oversight in the table above.

**DOC-008.** A requirement is satisfied when at least one document of that `doc_type` is attached.
Requirements are satisfied per document type, not per file.

**DOC-009.** The checklist response returns, per requirement: `doc_type`, `label_nl`, `label_en`,
`required`, `satisfied`. The full shape — which adds `reason` for conditional rows, the `documents[]`
attached to each requirement, and the `required_count` / `satisfied_count` totals — is canonical in
[`8-api.md`](8-api.md) §7.

**DOC-010.** The checklist is satisfied by document type *as declared on upload*. Nothing overrides
that — including the optional classifier in [`9-ai-classification.md`](9-ai-classification.md), which
compares the file to the declared type and warns on a mismatch but never changes `doc_type` or
satisfaction (AI-017). Field extraction remains cut (SCP-015).

**This is the point of the whole feature.** A static checklist is a design error, not a
simplification: the required set genuinely differs by borrower profile and property type — an
employee needs payslips, a self-employed borrower needs tax assessments and an accountant's
statement; an existing home needs an energy certificate, a new build needs a building permit and
construction quotes — and incomplete files are the dominant failure mode in Belgian mortgage
origination. A static checklist is a large part of why files arrive incomplete.

## 12. Application state machine

```
DRAFT
  → SUBMITTED            (borrower submits the form)
SUBMITTED
  → DOCUMENTS_PENDING    (automatic; checklist computed)
DOCUMENTS_PENDING
  → DOCUMENTS_COMPLETE   (every required doc_type satisfied)
DOCUMENTS_COMPLETE
  → DOCUMENTS_PENDING    (a document is removed or rejected)
  → UNDER_REVIEW         (manual advance; stands in for valuation, CKP, underwriting)
UNDER_REVIEW
  → OFFER_ISSUED         (out of scope to implement; terminal for the demo)
any non-terminal
  → WITHDRAWN
```

| ID | Transition | Trigger |
|---|---|---|
| APP-001 | `DRAFT → SUBMITTED` | Borrower submits the form |
| APP-002 | `SUBMITTED → DOCUMENTS_PENDING` | Automatic; checklist computed (DOC-005) |
| APP-003 | `DOCUMENTS_PENDING → DOCUMENTS_COMPLETE` | Every required `doc_type` satisfied (DOC-008) |
| APP-004 | `DOCUMENTS_COMPLETE → DOCUMENTS_PENDING` | A document is removed or rejected |
| APP-005 | `DOCUMENTS_COMPLETE → UNDER_REVIEW` | Manual advance |
| APP-006 | `UNDER_REVIEW → OFFER_ISSUED` | Out of scope to implement; terminal for the demo |
| APP-007 | `any non-terminal → WITHDRAWN` | Borrower withdraws |

Two properties that matter:

**APP-008. The cycle is not linear.** `DOCUMENTS_COMPLETE → DOCUMENTS_PENDING` is a real edge, not
an error path: a file moves back from complete to pending whenever a document is removed or fails
verification. In production this loop is the first-time-right problem.

**APP-009. Transitions are validated centrally.** One function owns the allowed edges; an invalid
transition raises rather than silently setting a field. → ERR-002

**APP-010.** `UNDER_REVIEW` collapses three separate real-world gates — property valuation, CKP
credit-register consultation, and credit assessment (SCP-018). Named as one state with a comment,
not silently omitted. Real lenders pass all three before issuing a binding offer, which is
accompanied by a standardised ESIS information sheet. CKP consultation has a 45-day validity window,
so it can expire and push a file backwards; CKP, ESIS and the reflection period are present here as
states, not implemented as integrations (SCP-012).

## 13. Validation and errors

- **ERR-001** — Domain rule violations return 422 with a machine-readable `code` and a human
  `message`. 422 is the **default**, not a blanket: a computation failure is 500 and a state
  conflict is 409. The status for every code is fixed in the registry, `7-validation.md` §2.
- **ERR-002** — Codes are stable strings. These five are required by the domain:
  `LOAN_AMOUNT_NOT_POSITIVE`, `TERM_OUT_OF_RANGE`, `UNSUPPORTED_DOCUMENT_TYPE`,
  `DOCUMENT_TOO_LARGE`, `INVALID_STATE_TRANSITION`. The full catalogue of 22, with statuses and
  messages, is the registry in `7-validation.md` §2.
- **ERR-003** — `UNSUPPORTED_DOCUMENT_TYPE` maps to 415, not 422. → DOC-001
- **ERR-004** — `DOCUMENT_TOO_LARGE` maps to 413, not 422. → DOC-002
- **ERR-005** — Not-found returns 404 without leaking whether the resource exists under another
  owner.
- **ERR-006** — An above-norm quotiteit is not an error and produces no code. → DOM-016

---

# Part III — Simulation Engine

Pure calculation. No database, no IO, no framework imports. This module is the one place in the
codebase where being wrong is not recoverable by good structure, so it is specified to the cent.

The simulation answers two questions for the borrower, and the second one matters more:

1. **What will I pay every month?** Monthly payment, total repaid, total interest, and the all-in
   cost as JKP alongside the headline rate.
2. **How much cash do I need on the day?** Own contribution plus purchase tax plus notary plus the
   lender's fees. This number is regularly two to three times the size the borrower expects, and it
   is where a Belgian simulator either earns credibility or loses it.

Everything in §20 is an acceptance criterion and belongs in the test suite. The numbers there were
computed, not estimated; a change that moves any of them is a regression, not a refinement.

## 14. Monthly rate

**SIM-001.** Belgian mortgage credit derives the annual rate from the periodic rate
**actuarially**, not by division. Anchored in art. I.9, 44° of the Wetboek van Economisch Recht: the
annual debit rate `I` and the periodic rate `i` satisfy `(1 + i)^n = (1 + I)`, where `n` is the
number of periods per year. For monthly periods:

```
i = (1 + I)^(1/12) - 1
```

**SIM-002. Not `I / 12`.** That convention is correct for Belgian *consumer* credit and for Dutch
mortgages, and it is what almost every online calculator uses. It is wrong here. The annual rate is
a derived, informational figure; the periodic rate is what actually applies to the outstanding
balance. Getting this right is the difference between output a Belgian lender recognises and output
they do not.

**SIM-003.** Sanity check that belongs in the test suite:

```
(1 + i)**12 == I + 1      # to within 1e-12
```

## 15. Monthly payment

**SIM-004.** Annuity, constant payment (`vaste maandlast`):

```
M = K * i / (1 - (1 + i)^(-n))
```

`K` = loan amount, `n` = term in months, `i` = monthly rate from §14.

**SIM-005. Zero-rate case:** when `I == 0`, the formula divides by zero. Return `K / n`.

**SIM-006.** `M` is rounded to 2 decimals for display and for the schedule.

**Totals are the sum of the schedule** — of the instalments actually charged — not `M × n`. The
schedule is built from the rounded payment, so this is what "computed from the rounded payment"
was reaching for; but `M × n` and the sum of the schedule are different numbers, because the final
instalment is adjusted (SIM-009) and because interest is rounded to the cent every month (SIM-008).

The sum is the one that reconciles. It is what the borrower actually pays, and it is the only
candidate for which `total_paid - loan_amount == total_interest` while the balance still closes at
exactly zero. See AC-003, where this was wrong.

**SIM-007.** Repayment type is an enum with one member, annuity. `vaste kapitaalaflossing` (linear),
`bullet` and `accordeon` all exist in the market and are cut (SCP-007); adding them is additive, not
a migration.

## 16. Amortisation schedule

**SIM-008.** Computed and tested; not rendered in the UI (SCP-013).

```
for each month:
    interest  = round(balance * i, 2)
    principal = M - interest
    balance   = balance - principal
```

**SIM-009.** The final instalment absorbs the rounding residue so the closing balance is exactly
`0.00`. → AC-006

## 17. Upfront costs

**SIM-010.**

```
registration_duty = property_value * rate(region, is_first_home)
notary_fee        = 3300           # flat stand-in for the degressive tariff
mortgage_costs    = round(loan_amount * 0.012, 2)
dossier_fee       = 350
valuation_fee     = 285

total_costs       = sum of the above
total_cash_needed = own_contribution + total_costs
```

### 17.1 Registration duty rates

Normative. Regional, and dependent on `enige eigen woning` (only own home) status.

**SIM-011.**

| Region | Standard | First home (`enige eigen woning`) |
|---|---|---|
| Flanders | 12% | **2%** |
| Wallonia | 12.5% | **3%** |
| Brussels | 12.5% | 12.5% on `max(0, price - 200 000)` |

**SIM-012.** Brussels applies an `abattement`: an allowance on the first slice of the price rather
than a reduced rate. This is a different mechanism and is implemented as such, not approximated with
a rate.

**SIM-013.** Purchase tax is paid from the buyer's own savings and cannot be financed. On a €300,000
house in Flanders the difference between first-home and non-first-home status is €30,000 of cash the
buyer must have on the day. A simulator that ignores this is not simplified, it is lying. → AC-005

### 17.2 Notary fee

**SIM-014.** The notary fee is a flat constant (`3300`) standing in for a degressive tariff set by
royal decree. Flagged here rather than hidden, so it is visible as a known simplification (SCP-016).

## 18. JKP / TAEG

**SIM-015.** The all-in annual cost, which the lender must disclose alongside the nominal rate.
Legally the rate that equates the present value of drawdowns to the present value of payments, using
the same actuarial convention as §14.

**SIM-016.** Costs that legally belong in JKP and are included here: `dossier_fee` (the file fee),
`valuation_fee`, and `mortgage_costs` (the notarial cost of registering the mortgage). Insurance
premiums belong in JKP only when the lender requires the policy be taken with them; no insurance is
modelled here.

**SIM-017.** Costs that do **not** belong in JKP and are excluded: `registration_duty` (a tax on the
purchase, not a cost of credit) and `notary_fee` for the purchase deed. Both are costs of buying a
house rather than costs of credit.

**SIM-018.** Solved numerically:

```
find r such that  sum over t in 1..n of  M / (1 + m(r))^t  ==  K - jkp_fees
where m(r) = (1 + r)^(1/12) - 1
```

Bisection on `r` in `[0.0001, 0.30]`, tolerance `1e-10`.

**SIM-019.** JKP is always `>= nominal rate`, and in practice strictly greater. A JKP equal to the
nominal rate means the fees were not applied and is a bug. → AC-008

## 19. Request and response

**SIM-020.** The request and response contract for `POST /api/simulations` is canonical in
[`8-api.md`](8-api.md) §4 — the endpoint table, both bodies, and the status code.

An earlier version of this rule carried the bodies inline and had three of them wrong: `200 OK` where
a created resource returns **201**, `"annual_nominal_rate": "0.04"` where `7-validation.md` VAL-019
requires four decimals (`"0.0400"`), and no `created_at`. The wire contract lives in one place now;
the **figures** stay here, as `AC-003`.

**SIM-021.** Monetary values are serialised as strings to survive JSON without float rounding.

## 20. Acceptance criteria

These are the tests. A change that breaks any of them is a regression.

### AC-001 — Reproduce a published bank example

KBC representative example: €170,000 over 240 months at 5.46%.

```
monthly_payment == 1152.95    (published: 1152.96, tolerance ±0.02)
```

The published figure derives from a rounded rate, hence the one-cent tolerance. Computing the same
input with `I / 12` gives **1165.57**, off by €12.62 a month. That gap is the test. → SIM-002

### AC-002 — Rate conversion

```
i = monthly_rate(Decimal("0.0546"))
i == 0.00443996 to 8 dp
(1 + i)**12 == 1.0546 to 1e-12
i != Decimal("0.0546") / 12
```

### AC-003 — Primary case, end to end

€300,000 property, €30,000 own contribution, 300 months, 4.00%, Flanders, first home.

```
loan_amount        == 270000.00
quotiteit          == 0.9000
monthly_payment    == 1414.52
total_paid         == 424356.04
total_interest     == 154356.04
total_cash_needed  ==  43175.00
```

**The two totals were `424355.98` and `154355.98` until T07, and they were wrong.** That figure is
the *unrounded* payment times the term — `1414.519936… × 300 = 424355.9809…` — which is neither what
SIM-006 asked for nor what SIM-008 produces. Three candidates existed and only one survives:

| Candidate | Value | Why not |
|---|---|---|
| rounded `M × n` | `424356.00` | SIM-006 as literally worded, but nobody pays `M` in the final month |
| unrounded `M × n` | `424355.98` | what this criterion recorded; an abstraction no schedule produces |
| **sum of the schedule** | **`424356.04`** | **holds** |

Only the third satisfies all of: the balance closes at exactly `0.00` (SIM-009, AC-006), the capital
instalments sum to the loan amount (AC-006), and `total_paid - loan_amount == total_interest`. The
first two each break at least one of those. Since SIM-008 and SIM-009 are the normative algorithm and
AC-003 is a figure derived from it, the algorithm wins and the figure is corrected.

### AC-004 — Regional tax matrix

Property €300,000.

| Region | First home | `registration_duty` |
|---|---|---|
| Flanders | true | 6 000.00 |
| Flanders | false | 36 000.00 |
| Wallonia | true | 9 000.00 |
| Wallonia | false | 37 500.00 |
| Brussels | true | 12 500.00 |
| Brussels | false | 37 500.00 |

Brussels first-home: `(300 000 - 200 000) * 0.125 = 12 500.00`.

### AC-005 — Same house, two tax statuses

Flanders, €300,000, €30,000 own contribution:

```
first_home=True   -> total_cash_needed == 43175.00
first_home=False  -> total_cash_needed == 73175.00
```

A €30,000 difference on the same house and the same loan. This is the number a real Belgian borrower
cares about most and the one a naive simulator never shows.

### AC-006 — Schedule closes

For the primary case, the sum of principal instalments equals the loan amount exactly and the
closing balance is `0.00`.

### AC-007 — Edge cases

```
zero rate:      120000 over 240 months at 0.00%  -> 500.00
one month term: term_months = 12 is accepted; 11 raises TERM_OUT_OF_RANGE
own contribution == property_value  -> LOAN_AMOUNT_NOT_POSITIVE
quotiteit 0.95   -> valid, above_supervisory_norm == true
```

### AC-008 — JKP exceeds nominal

For the primary case, `jkp > nominal_rate` strictly, and `jkp ≈ 0.0414`.

### AC-009 — Affordability bands

Household of one adult, no dependants, `net_monthly_income = 3200.00`, no existing credit, against
the primary case's monthly payment of `1414.52`:

```
monthly_obligations == 1414.52
dsti                == 0.4420        -> above DSTI_TIGHT_MAX (0.40)
residual_income     == 1785.48
residual_floor      == 1200.00       -> comfortable on residual
band                == OUTSIDE_TYPICAL_NORMS   # the worse of the two, SIM-026
```

The same household on `net_monthly_income = 4800.00`:

```
dsti                == 0.2947        -> comfortable
residual_income     == 3385.48
band                == COMFORTABLE
```

`net_monthly_income = None` returns `INSUFFICIENT_DATA` with `dsti` and `residual_income` both null,
and never raises. → SIM-027

## 21. Affordability

Numbered last, though it belongs beside the application sections (§9.4, §11, §12). Inserting it there
would renumber every section after it, and the `§` column of Appendix A is published — *supersede,
never renumber* (`specs/README.md`). Added at T53.

**This section supersedes SCP-011.** Both properties that made the cut defensible are kept: the
assessment is application-scoped rather than part of the public simulator, and it produces an
advisory band, never a decision.

### 21.1 The data it reads

**DOM-029. The confirmed financial profile.** One row per application, separate from `borrowers`.

| Field | Type | Note |
|---|---|---|
| `net_monthly_income` | Decimal, nullable | Household net monthly income |
| `existing_credit_monthly` | Decimal, nullable | Total monthly instalments on existing credit |
| `dependants` | int | People dependent on the household, beyond the borrowers themselves |

Every value carries **provenance**: `MANUAL` when the borrower typed it, `DOCUMENT` when it was read
off a document *and the borrower confirmed it*, with the source `document_id` and `confirmed_at`.
An underwriter needs to know which of the two a number is, and it is the audit trail
`9-ai-classification.md` AI-003 already argues for.

**It is a separate table, not columns on `borrowers`, for a concrete reason:** `8-api.md` API-037
replaces the borrower collection wholesale on every PATCH, so anything stored there is destroyed the
next time the borrower edits the wizard.

**DOM-030. Only confirmed data is ever assessed.** A value read from a document is a *proposal* until
the borrower confirms it, and a proposal is never an input here. This is AI-003 — "the model advises,
deterministic code owns the outcome" — applied to a document's *values* rather than to its *type*,
and it is what keeps the assessment defensible when the classifier is wrong. With no documents
uploaded at all, every value is `MANUAL` and the assessment works exactly the same.

### 21.2 The two measures

**SIM-022. Monthly obligations** are the mortgage payment plus every other monthly credit
instalment:

```
monthly_obligations = mortgage_monthly_payment + existing_credit_monthly
```

The mortgage payment is passed in as a `Decimal` (§15), not recomputed here: the affordability module
does not import the simulation domain.

**SIM-023. DSTI** — debt service to income — is the share of net income committed to credit:

```
dsti = monthly_obligations / net_monthly_income        # 4 dp, ROUND_HALF_UP, like quotiteit
```

| DSTI | Band |
|---|---|
| `<= 0.33` | `COMFORTABLE` |
| `<= 0.40` | `TIGHT` |
| `> 0.40` | `OUTSIDE_TYPICAL_NORMS` |

**SIM-024. `Restleefgeld`** — residual living income — is what remains after every credit obligation,
against a floor that grows with the household:

```
residual_income = net_monthly_income - monthly_obligations
residual_floor  = 1200 + 400 * (adults - 1) + 300 * dependants
```

`adults` is the number of borrowers on the application (DOM-021), so a joint application raises the
floor without a second field to fill in.

| Residual | Band |
|---|---|
| `>= floor * 1.10` | `COMFORTABLE` |
| `>= floor` | `TIGHT` |
| `< floor` | `OUTSIDE_TYPICAL_NORMS` |

**SIM-025. Every threshold and floor constant above is a named module constant, never a literal.**
They are the entire tuning surface of this feature and the first thing a reviewer will ask about —
the same discipline `9-ai-classification.md` AI-016 imposes on the confidence thresholds.

**SIM-026. The reported band is the worse of the two.** Passing on income share while failing on
residual income is not a pass. Ordering: `COMFORTABLE < TIGHT < OUTSIDE_TYPICAL_NORMS`.

**SIM-027. Missing income yields `INSUFFICIENT_DATA`, never an exception and never a zero.**
`net_monthly_income` is nullable, and dividing by it unguarded is the obvious bug here. `dsti` and
`residual_income` are null in that band. A missing `existing_credit_monthly` is different — it is
treated as zero, because "no existing credit" is the common case and the borrower says so with the
`has_existing_credit` flag they already answered (DOM-022).

### 21.3 It is a band, never a decision

**SIM-028.** The output is `COMFORTABLE` / `TIGHT` / `OUTSIDE_TYPICAL_NORMS` / `INSUFFICIENT_DATA`.
It is never "approved" or "rejected", and nothing in the application state machine (§12) reads it.

This is the same treatment an above-norm quotiteit already gets (DOM-016: flagged, explained, never
rejected), and for the same reason. Oper is explicit that their own credit analyst applies a written
policy and is *not credit scoring*, with a human in the loop — an assessment that returned a verdict
would be the thing this whole design is arguing against.

**SIM-029. The constants are representative lender norms, not law.** The ~33% income share is an
informal underwriting convention, not a statutory cap, and residual-income floors are bank-internal
and vary between lenders. They are flagged here exactly as SIM-014 flags the standing-in notary fee
(SCP-016), so that the simplification is visible rather than hidden behind a plausible-looking number.
The NBB's published expectations govern **quotiteit** (§9.2), which is why that one is normative here
and these are not.

---

# Appendix A — Traceability

Source shorthand: **00** = `00-scope.md`, **01** = `01-domain.md`, **02** = `02-simulation.md`.
Where two sources are listed, this document carries the union of both — see Appendix B.

## Scope (`SCP-`)

| ID | Statement | Source | § |
|---|---|---|---|
| SCP-001 | Scope in one sentence | 00 · Scope, in one sentence | §1.1 |
| SCP-002 | Simulate — anonymous, no account | 00 · What we are building | §1.2 |
| SCP-003 | Sign up — simulation follows the borrower | 00 · What we are building | §1.2 |
| SCP-004 | Apply — multi-step borrower file | 00 · What we are building | §1.2 |
| SCP-005 | Upload documents against a derived checklist | 00 · What we are building | §1.2 |
| SCP-006 | Cut: variable rates | 00 · Deliberately not built | §5 |
| SCP-007 | Cut: non-annuity repayment types | 00 · Deliberately not built | §5 |
| SCP-008 | Cut: new-build VAT | 00 · Deliberately not built | §5 |
| SCP-009 | Cut: Flemish reductions | 00 · Deliberately not built | §5 |
| SCP-010 | Cut: co-borrowers in the UI | 00 · Deliberately not built | §5 |
| SCP-011 | Superseded at T53: affordability is built, advisory only | 00 · Deliberately not built | §5, §21 |
| SCP-012 | Cut: CKP, ESIS, reflection period | 00 · Deliberately not built | §5 |
| SCP-013 | Cut: amortisation schedule in the UI | 00 · Deliberately not built | §5 |
| SCP-014 | Cut: independent property valuation | 00 · Deliberately not built | §5 |
| SCP-015 | Cut: field extraction and cross-document checking | 00 · Deliberately not built, narrowed by `9-ai-classification.md` | §5 |
| SCP-016 | Simplification: flat notary fee | 00 · Simplifications | §6 |
| SCP-017 | Simplification: appraised value = purchase price | 00 · Simplifications | §6 |
| SCP-018 | Simplification: `UNDER_REVIEW` collapses 3 gates | 00 · Simplifications | §6 |
| SCP-019 | DoD: deployed URL, four flows, no debugging | 00 · Definition of done | §7 |
| SCP-020 | DoD: reproduces a published bank example | 00 · Definition of done | §7 |
| SCP-021 | DoD: purchase tax correct, 3 regions × 2 statuses | 00 · Definition of done | §7 |
| SCP-022 | DoD: checklist reacts to employment / property type | 00 · Definition of done | §7 |
| SCP-023 | DoD: application can move backwards | 00 · Definition of done | §7 |
| SCP-024 | DoD: `Decimal` everywhere, schedule closes at zero | 00 · Definition of done | §7 |

## Domain (`DOM-`)

| ID | Statement | Source | § |
|---|---|---|---|
| DOM-001 | Derived data is computed, never stored | 01 · preamble | preamble |
| DOM-002 | Rules live in the domain, not the API or the form | 01 · preamble | preamble |
| DOM-003 | `Decimal`, never `float` | 01 · Money | §8 |
| DOM-004 | Quantised to 2 dp, `ROUND_HALF_UP` | 01 · Money | §8 |
| DOM-005 | Rates as fractions, not percentages | 01 · Money | §8 |
| DOM-006 | Periodic rate at full precision; 6 dp quoting | 01 · Money | §8 |
| DOM-007 | `Region` enum drives purchase tax only | 01 · Region | §9.1 |
| DOM-008 | Simulation is anonymous by default; field table | 01 · Simulation | §9.2 |
| DOM-009 | Derived fields of a simulation | 01 · Simulation | §9.2 |
| DOM-010 | `10 000 <= property_value <= 10 000 000` | 01 · Invariants, narrowed by `7-validation.md` | §9.2 |
| DOM-011 | `0 <= own_contribution < property_value` | 01 · Invariants | §9.2 |
| DOM-012 | `loan_amount = value - contribution`, `> 0` | 01 · Invariants | §9.2 |
| DOM-013 | `12 <= term_months <= 360` | 01 · Invariants | §9.2 |
| DOM-014 | `0 <= annual_nominal_rate <= 0.20` | 01 · Invariants | §9.2 |
| DOM-015 | `quotiteit = loan_amount / property_value` | 01 · Invariants | §9.2 |
| DOM-016 | Above 90% is flagged, never rejected | 00 · Quotiteit + 01 · Invariants | §9.2 |
| DOM-017 | Lenders price in bands by quotiteit | 00 · Quotiteit | §9.2 |
| DOM-018 | Quotiteit is against value, not price | 00 · Deliberately not built | §9.2 |
| DOM-019 | User fields; email unique, case-insensitive | 01 · User | §9.3 |
| DOM-020 | No real personal data; test data only | 01 · User | §9.3 |
| DOM-021 | `borrowers` is a collection from the start | 00 · cut table + 01 · Application | §9.4 |
| DOM-022 | Borrower fields and `employment_type` enum | 01 · Application | §9.4 |
| DOM-023 | Income captured, not used for a decision | 00 · cut table + 01 · Application | §9.4 |
| DOM-024 | First-home flag is application-level | 01 · Application | §9.4 |
| DOM-025 | Anonymous simulation is attached on signup | 01 · Claiming a simulation | §10 |
| DOM-026 | Anonymous `id` held client-side | 01 · Claiming a simulation | §10 |
| DOM-027 | Attach iff `user_id` is null; never reassign | 01 · Claiming a simulation | §10 |
| DOM-028 | Borrower aged 18 – 75 at submission | added for `7-validation.md` | §9.4 |
| DOM-029 | The confirmed financial profile, with provenance | added at T53 | §21.1 |
| DOM-030 | Only confirmed data is assessed; a proposal is not an input | added at T53 | §21.1 |

## Documents (`DOC-`)

| ID | Statement | Source | § |
|---|---|---|---|
| DOC-001 | Accepted content types; else 415 | 01 · Document | §9.5 |
| DOC-002 | 10 MB limit; over that 413 | 01 · Document | §9.5 |
| DOC-003 | `storage_key` opaque, never a user path | 01 · Document | §9.5 |
| DOC-004 | `filename` sanitised | 01 · Document | §9.5 |
| DOC-005 | Checklist is derived, not stored | 01 · Document checklist | §11 |
| DOC-006 | Base requirements (identity, statements, compromis) | 01 · Document checklist | §11 |
| DOC-007 | Five conditional requirement rules | 00 · Why not CRUD + 01 · Document checklist | §11 |
| DOC-008 | Satisfied per `doc_type`, not per file | 00 · Document set + 01 · Document checklist | §11 |
| DOC-009 | Checklist response shape — full form in `8-api.md` §7 | 01 · Document checklist | §11 |
| DOC-010 | Type as declared on upload; the classifier never overrides it | 00 · cut table | §11 |
| DOC-011 | `employment_type` `OTHER` adds no requirement, deliberately | added — the enum allowed it with no rule | §11 |

## Application lifecycle (`APP-`)

| ID | Statement | Source | § |
|---|---|---|---|
| APP-001 | `DRAFT → SUBMITTED` | 01 · State machine | §12 |
| APP-002 | `SUBMITTED → DOCUMENTS_PENDING` | 01 · State machine | §12 |
| APP-003 | `DOCUMENTS_PENDING → DOCUMENTS_COMPLETE` | 01 · State machine | §12 |
| APP-004 | `DOCUMENTS_COMPLETE → DOCUMENTS_PENDING` | 01 · State machine | §12 |
| APP-005 | `DOCUMENTS_COMPLETE → UNDER_REVIEW` | 01 · State machine | §12 |
| APP-006 | `UNDER_REVIEW → OFFER_ISSUED` | 01 · State machine | §12 |
| APP-007 | `any non-terminal → WITHDRAWN` | 01 · State machine | §12 |
| APP-008 | The cycle is not linear | 00 · Application lifecycle + 01 · State machine | §12 |
| APP-009 | Transitions validated centrally, one owner | 01 · State machine | §12 |
| APP-010 | `UNDER_REVIEW` = valuation + CKP + assessment; CKP 45 days; ESIS | 00 · lifecycle, Simplifications, cut table + 01 · State machine | §12 |

## Errors (`ERR-`)

| ID | Statement | Source | § |
|---|---|---|---|
| ERR-001 | 422 with machine-readable `code` and `message` | 01 · Validation and errors | §13 |
| ERR-002 | Five stable error codes | 01 · Validation and errors | §13 |
| ERR-003 | `UNSUPPORTED_DOCUMENT_TYPE` → 415 | 01 · Document | §13 |
| ERR-004 | `DOCUMENT_TOO_LARGE` → 413 | 01 · Document | §13 |
| ERR-005 | 404 without leaking cross-owner existence | 01 · Validation and errors | §13 |
| ERR-006 | Above-norm quotiteit produces no error | 01 · Simulation | §13 |

## Simulation engine (`SIM-`)

| ID | Statement | Source | § | Test |
|---|---|---|---|---|
| SIM-001 | `i = (1 + I)^(1/12) - 1`, WER art. I.9, 44° | 00 · Interest convention + 02 §1 | §14 | AC-002 |
| SIM-002 | Not `I / 12` — consumer-credit convention is wrong here | 00 · Why not CRUD + 02 §1 | §14 | AC-001, AC-002 |
| SIM-003 | `(1 + i)**12 == I + 1` within `1e-12` | 02 §1 | §14 | AC-002 |
| SIM-004 | `M = K * i / (1 - (1 + i)^(-n))` | 02 §2 | §15 | AC-003 |
| SIM-005 | Zero-rate case returns `K / n` | 02 §2 | §15 | AC-007 |
| SIM-006 | `M` rounded to 2 dp; totals from the rounded payment | 02 §2 | §15 | AC-003 |
| SIM-007 | Repayment type is an enum with one member | 00 · cut table + 02 §2 | §15 | — |
| SIM-008 | Schedule loop (interest, principal, balance) | 02 §3 | §16 | AC-006 |
| SIM-009 | Final instalment absorbs the residue; closes at `0.00` | 02 §3 | §16 | AC-006 |
| SIM-010 | Upfront cost formulas and constants | 02 §4 | §17 | AC-003 |
| SIM-011 | Regional registration duty rates | 00 · Registratierechten + 02 §4 | §17.1 | AC-004 |
| SIM-012 | Brussels `abattement` is an allowance, not a rate | 00 · Registratierechten + 02 §4 | §17.1 | AC-004 |
| SIM-013 | Tax is paid from savings, cannot be financed | 00 · Why not CRUD | §17.1 | AC-005 |
| SIM-014 | Notary fee is a flat `3300` stand-in | 00 · Simplifications + 02 §4 | §17.2 | — |
| SIM-015 | JKP definition and disclosure obligation | 00 · JKP/TAEG + 02 §5 | §18 | AC-008 |
| SIM-016 | JKP inclusions; insurance only when required by lender | 00 · JKP/TAEG + 02 §5 | §18 | AC-008 |
| SIM-017 | JKP exclusions: purchase tax and deed notary fee | 00 · JKP/TAEG + 02 §5 | §18 | AC-008 |
| SIM-018 | Bisection on `[0.0001, 0.30]`, tolerance `1e-10` | 02 §5 | §18 | AC-008 |
| SIM-019 | JKP `>=` nominal; equality means the fees were not applied | 00 · JKP/TAEG + 02 §5 | §18 | AC-008 |
| SIM-020 | The wire contract — canonical in `8-api.md` §4 | 02 §6 | §19 | AC-003 |
| SIM-021 | Money serialised as JSON strings | 02 §6 | §19 | — |
| SIM-022 | Monthly obligations = mortgage payment + other credit | added at T53 | §21.2 | — |
| SIM-023 | DSTI formula and its three bands | added at T53 | §21.2 | AC-009 |
| SIM-024 | `Restleefgeld` floor and its three bands | added at T53 | §21.2 | AC-009 |
| SIM-025 | Every threshold is a named constant | added at T53 | §21.2 | — |
| SIM-026 | The reported band is the worse of the two | added at T53 | §21.2 | AC-009 |
| SIM-027 | Missing income is `INSUFFICIENT_DATA`, never an exception | added at T53 | §21.2 | AC-009 |
| SIM-028 | A band, never a decision; the state machine never reads it | added at T53 | §21.3 | — |
| SIM-029 | The constants are representative lender norms, not law | added at T53 | §21.3 | — |

## Acceptance criteria (`AC-`)

| ID | Statement | Source | § |
|---|---|---|---|
| AC-001 | KBC example: €170,000 / 240 months / 5.46% → `1152.95` | 02 §7.1 | §20 |
| AC-002 | Rate conversion to 8 dp; `!= I / 12` | 02 §7.2 | §20 |
| AC-003 | Primary case end to end | 02 §7.3 | §20 |
| AC-004 | Regional tax matrix, six rows | 02 §7.4 | §20 |
| AC-005 | Same house, two tax statuses: €30,000 apart | 02 §7.5 | §20 |
| AC-006 | Schedule closes at exactly `0.00` | 02 §7.6 | §20 |
| AC-007 | Edge cases: zero rate, term bounds, LTV 0.95 | 02 §7.7 | §20 |
| AC-008 | `jkp > nominal_rate` strictly; `≈ 0.0414` | 02 §7.8 | §20 |
| AC-009 | Affordability bands, both directions and the null case | added at T53 | §20 |

# Appendix B — Source coverage

Every heading of the three merged documents and where it landed. Nothing was dropped.

| Source section | Target |
|---|---|
| 00 · What we are building | §1 |
| 00 · Why this is not a CRUD app | §2 (arithmetic → §14, cost of buying → §17, document set → §11) |
| 00 · What the reviewer is scoring | §3 |
| 00 · Scope, in one sentence | §1.1 |
| 00 · Belgian market context (6 facts) | §4, normative text at §14, §9.2, §17.1, §18, §11, §12 |
| 00 · Deliberately not built (10 rows) | §5 |
| 00 · Simplifications (3) | §6 |
| 00 · Definition of done (6) | §7 |
| 01 · preamble (2 governing rules) | preamble |
| 01 · Money | §8 |
| 01 · Region / Simulation / User / Application / Document | §9.1 – §9.5 |
| 01 · Claiming a simulation | §10 |
| 01 · Document checklist | §11 |
| 01 · Application state machine | §12 |
| 01 · Validation and errors | §13 |
| 02 · preamble (two questions, test-suite note) | Part III preamble |
| 02 §1 Monthly rate | §14 |
| 02 §2 Monthly payment | §15 |
| 02 §3 Amortisation schedule | §16 |
| 02 §4 Upfront costs | §17, §17.1, §17.2 |
| 02 §5 JKP / TAEG | §18 |
| 02 §6 Request and response | §19 |
| 02 §7.1 – §7.8 Acceptance criteria | §20, AC-001 – AC-008 |
