---
id: UX
title: UX
status: draft
version: 1.0.0
owner: paketoff
updated: 2026-08-29
---

# 4 — UX

Companion to [`3-ui.md`](3-ui.md), which covers colour, type and components. This document covers
**behaviour**: what happens, in what order, and what the borrower sees while it happens.

Where a value and a behaviour describe the same thing, `3-ui.md` owns the value and this file owns
the behaviour. Edge cases and validation messages will live in `7-validation.md` — **not yet
written**.

## 1. Principle

The borrower is not filling in a form. They are trying to answer one question — *can I afford this,
and how much money do I need on the day?* — and every interaction either moves them toward that
answer or gets in the way.

Two consequences that drive most of the rules below:

- **UX-001. The interface starts with an answer, not a blank.** Prefilled, computed, visible on load.
- **UX-002. Nothing is asked twice.** Anything the borrower has already told us is carried forward.

## 2. Responsive

**UX-003. Mobile-first, and it is not a separate task.**

Tailwind is mobile-first by default. Build for the phone, add `md:` where a wider layout genuinely
helps. Done this way, responsiveness costs roughly five classes across the whole application. Done in
reverse — desktop first, adapt later — it costs an hour we do not have.

What that means in practice:

- **UX-004** — Single column everywhere. Page width: `3-ui.md` UI-056.
- **UX-005** — Exactly one two-column layout: the simulator on `md:` and up, form left, result right.
  Layout detail: `3-ui.md` UI-054.
- **UX-006** — No mobile menu, no drawers, no gestures, no separate mobile route.
- **UX-007** — Touch targets at least 44px tall.
- **UX-008** — Inputs do not zoom on focus. Font-size: `3-ui.md` UI-044.

**Why it matters here beyond aesthetics:** the reviewer may open the deployed link on a phone before
the call. A broken layout lands directly in the "does it work" scoring dimension. This is cheap
insurance, not polish.

## 3. Simulator

### 3.1 Opens with an answer

**UX-009.** The form is **prefilled with a realistic Belgian scenario** and the result is already
computed on first paint. No empty state, no "calculate" button, no zero values.

```
property_value        300 000
own_contribution       30 000
term_months               300   (25 years)
annual_nominal_rate      4.00 %
region                FLANDERS
is_first_home            true
```

**UX-010.** These are exactly the inputs of `0-business-logic.md` **AC-003**, the primary
acceptance case. The opening screen and the test suite assert the same numbers on purpose: if the
prefill changes, AC-003 changes with it, and neither moves alone.

A form of six empty fields is work. A prefilled one is a toy the borrower starts adjusting within
seconds. This is the single highest-leverage UX decision in the build.

### 3.2 The rate is prefilled, and labelled as indicative

**UX-011.** The borrower has no idea what rate they will be offered. Asking for it as a cold empty
field pushes a question onto them that they cannot answer.

Prefill with a market rate and label it: *"Indicative market rate. Your actual rate depends on your
profile and quotiteit."* Keep it editable.

### 3.3 Live recalculation

- **UX-012** — No calculate button. Recompute on change, debounced at 300ms.
- **UX-013** — **The previous result stays on screen while the new one is computed.** Not blanked,
  not covered by a spinner, not collapsed. If a request is in flight, the panel dims slightly and
  nothing moves. Otherwise, dragging a value makes the numbers flash and it reads as a bug.
- **UX-014** — In-flight requests are cancelled when a newer one starts, so a slow response cannot
  overwrite a newer result.

### 3.4 Two numbers of equal weight

**UX-015.** The result panel leads with two figures at the same visual scale:

- **Monthly payment** — what they expected to see.
- **Total cash needed on the day** — what they did not.

Most simulators show the first and bury or omit the second. Showing both, equally, is the product
argument of this build. The cash figure sits on the signal surface described in `3-ui.md` UI-048.

**UX-016.** Below them, secondary and smaller: total repaid, total interest, JKP next to the nominal
rate, quotiteit.

### 3.5 Quotiteit updates visibly

**UX-017.** As the borrower moves their own contribution, quotiteit recalculates in front of them and
crosses the 90% mark. When it goes above, a chip appears: *"Above the 90% supervisory norm —
possible, but usually at a higher rate."*

Informational, never an error — `0-business-logic.md` DOM-016, ERR-006; styling `3-ui.md` UI-050.
This turns the calculator into an explanation of how the lending decision actually works, which is
the difference between a widget and a product.

### 3.6 Region and first-home are primary fields

**UX-018.** These two inputs change the answer by €30,000 (SIM-013, AC-005). They are not in an
"advanced options" accordion.

**UX-019.** The first-home checkbox carries one line of help text, because `enige eigen woning` is a
tax term and the borrower is not required to know it: *"Reduced purchase tax applies if this will be
your only home."*

### 3.7 Cost breakdown is expandable, and collapsed by default

**UX-020.** The cash-needed figure is the headline. The five-line breakdown of how it is composed
sits behind a disclosure, expanded with one click, closed by default. Present but not shouting.

## 4. Validation behaviour

Rules and message text will live in `7-validation.md` (not yet written). What belongs here is *when*
validation fires.

- **UX-021** — **On blur, never on keystroke.** A borrower typing "3" on the way to "300000" must not
  be told the value is too small.
- **UX-022** — **Currency formatting on blur.** While the field has focus, leave the raw input alone.
- **UX-023** — **Error messages come from backend error codes**, never hardcoded in the template. One
  source of truth for what a rule means — `0-business-logic.md` ERR-002, `1-code-quality.md` CQ-063.
- **UX-024** — **Server errors appear next to the field they concern**, not as a toast. A toast for a
  field error makes the borrower hunt for the problem. Visual treatment: `3-ui.md` UI-046.
- **UX-025** — Once a field has errored, it revalidates on change so the error clears as soon as it
  is fixed.

## 5. Sign up, and carrying the simulation across

**UX-026.** After signing up, the borrower does **not** land on an empty dashboard. They land on an
application prefilled from the simulation they just ran.

They already told us the price, the region and their first-home status. Asking again is the fastest
way to lose them, and it wastes the anonymous-simulation model we deliberately built.

**UX-027.** The flow — implements `0-business-logic.md` DOM-025 – DOM-027 and the cross-domain edge
`2-architecture.md` ARC-017:

1. Simulator holds the anonymous simulation id client-side.
2. Sign-up sends it along with the credentials.
3. The backend attaches the simulation to the new user, then creates a draft application seeded from
   it.
4. The borrower lands on step 1 of the wizard with the property section already filled.

**UX-028.** If the id is missing or already claimed, sign-up still succeeds and the wizard opens
empty. Losing a simulation must never block registration.

## 6. Application wizard

**UX-029.** Four steps: borrower → property → loan → review.

- **UX-030** — **Progress is always visible.** Which step, how many, which are done.
- **UX-031** — **Back always works** and never loses input.
- **UX-032** — **Only the current step validates.** Never pre-validate steps the borrower has not
  reached.
- **UX-033** — **The draft is saved server-side after step 1.** A refresh, a phone call, a closed tab
  — none of them destroy the input. This is a five-minute feature that saves the whole flow.
- **UX-034** — **The review step is editable**: each section has an edit link that jumps back to its
  step, and returns to review afterwards.
- **UX-035** — Submit is a single explicit action on the review step, disabled while in flight.

## 7. Documents

### 7.1 Upload per requirement, not one general dropzone

**UX-036.** Each checklist row has its own upload control. A single "drop files here" zone pushes the
classification decision onto the borrower, and that is precisely where incomplete files come from.

**UX-037.** Each row shows: the document type, the Dutch term, whether it is required, and its
current state. → `0-business-logic.md` DOC-009.

### 7.2 The checklist explains itself

**UX-038.** When a requirement appears because of an answer the borrower gave, say so: *"Required
because you selected employed"*. It stops the list feeling arbitrary and it demonstrates that the
checklist is derived, not fixed — DOC-005 – DOC-008.

### 7.3 Progress is explicit

**UX-039.** A count at the top: *"4 of 7 required documents uploaded."* When the last one lands, the
application status changes to complete and the change is visible without a reload — APP-003.

### 7.4 Upload behaviour

- **UX-040** — Optimistic: the row moves to uploading immediately.
- **UX-041** — On failure, the row reverts and shows the reason inline. No silent failures.
- **UX-042** — Accepted types and the size limit are stated **before** the borrower picks a file, not
  after it is rejected — DOC-001, DOC-002.
- **UX-043** — Removing a document moves the application back to pending, and that transition is
  shown, not hidden. It is a normal state change, not a failure — APP-004, ARC-018.

## 8. Loading and empty states

- **UX-044** — **Never a full-page spinner** after first load. Sections load independently.
- **UX-045** — Buttons that trigger a request show a spinner inside themselves and disable,
  preventing double submission by construction.
- **UX-046** — Empty states say what to do next, not that something is empty. "Upload your first
  document to get started", not "No documents".
- **UX-047** — Any list that can be empty has a written empty state. Blank areas read as bugs.

## 9. Not doing

Cut deliberately, and worth being able to say why:

| ID | Not doing | Why |
|---|---|---|
| UX-048 | Tooltips on every field | Help text under the two fields that genuinely need it. The rest are self-explanatory and tooltips do not work on touch. |
| UX-049 | Onboarding tour | Four screens. If they need a tour, the design failed. |
| UX-050 | Toasts for every action | Toasts only for actions with no other visible result. Everything else confirms itself by changing on screen. |
| UX-051 | Confirmation modals | Only for destructive and irreversible actions. Deleting a document is reversible: re-upload it. |
| UX-052 | Entrance animations, scroll reveals, skeleton shimmer | Motion budget in `3-ui.md` UI-022. In a financial interface these read as lag. |
| UX-053 | Dark mode toggle | One theme, done well. |
| UX-054 | Autosave on the simulator | It is anonymous and free to re-run. Persisting it adds state for no gain. |

## 10. Definition of done

- **UX-055** — The simulator shows a computed result on first paint with no interaction.
- **UX-056** — Changing any input updates the result without the previous value disappearing.
- **UX-057** — Quotiteit crossing 90% shows an informational chip, not an error.
- **UX-058** — Signing up from a simulation lands on a prefilled application.
- **UX-059** — Refreshing mid-wizard loses nothing after step 1.
- **UX-060** — Every checklist row has its own upload control and explains why it is required.
- **UX-061** — The entire flow completes on a 375px-wide viewport.

---

# Appendix A — Traceability

Source: `06-ux.md`, superseded by this document.

| ID | Statement | Source § | § |
|---|---|---|---|
| UX-001 | The interface starts with an answer, not a blank | Principle | §1 |
| UX-002 | Nothing is asked twice | Principle | §1 |
| UX-003 | Mobile-first, and not a separate task | 1 Responsive | §2 |
| UX-004 | Single column everywhere | 1 Responsive | §2 |
| UX-005 | Exactly one two-column layout | 1 Responsive | §2 |
| UX-006 | No mobile menu, drawers, gestures or mobile route | 1 Responsive | §2 |
| UX-007 | Touch targets at least 44px | 1 Responsive | §2 |
| UX-008 | Inputs do not zoom on focus | 1 Responsive | §2 |
| UX-009 | The simulator is prefilled and computed on first paint | 2 Opens with an answer | §3.1 |
| UX-010 | The prefill is exactly AC-003 | 2 Opens with an answer | §3.1 |
| UX-011 | The rate is prefilled and labelled indicative | 2 The rate is prefilled | §3.2 |
| UX-012 | No calculate button; recompute debounced at 300ms | 2 Live recalculation | §3.3 |
| UX-013 | The previous result stays on screen | 2 Live recalculation | §3.3 |
| UX-014 | In-flight requests are cancelled by newer ones | 2 Live recalculation | §3.3 |
| UX-015 | Two figures of equal weight | 2 Two numbers of equal weight | §3.4 |
| UX-016 | Secondary figures below, smaller | 2 Two numbers of equal weight | §3.4 |
| UX-017 | Quotiteit updates visibly; chip above 90% | 2 Quotiteit updates visibly | §3.5 |
| UX-018 | Region and first-home are primary fields | 2 Region and first-home | §3.6 |
| UX-019 | Help text on the first-home checkbox | 2 Region and first-home | §3.6 |
| UX-020 | Cost breakdown expandable, collapsed by default | 2 Cost breakdown | §3.7 |
| UX-021 | Validate on blur, never on keystroke | 3 Validation behaviour | §4 |
| UX-022 | Currency formatting on blur | 3 Validation behaviour | §4 |
| UX-023 | Error messages come from backend error codes | 3 Validation behaviour | §4 |
| UX-024 | Server errors appear next to their field, not as a toast | 3 Validation behaviour | §4 |
| UX-025 | An errored field revalidates on change | 3 Validation behaviour | §4 |
| UX-026 | Sign-up lands on a prefilled application, not a dashboard | 4 Sign up | §5 |
| UX-027 | The four-step claim-and-seed flow | 4 Sign up | §5 |
| UX-028 | A missing or claimed id never blocks registration | 4 Sign up | §5 |
| UX-029 | Four wizard steps | 5 Application wizard | §6 |
| UX-030 | Progress is always visible | 5 Application wizard | §6 |
| UX-031 | Back always works and never loses input | 5 Application wizard | §6 |
| UX-032 | Only the current step validates | 5 Application wizard | §6 |
| UX-033 | The draft is saved server-side after step 1 | 5 Application wizard | §6 |
| UX-034 | The review step is editable | 5 Application wizard | §6 |
| UX-035 | Submit is one explicit action, disabled in flight | 5 Application wizard | §6 |
| UX-036 | Upload per requirement, not one dropzone | 6 Upload per requirement | §7.1 |
| UX-037 | Each row shows type, Dutch term, required, state | 6 Upload per requirement | §7.1 |
| UX-038 | The checklist explains why a row is required | 6 The checklist explains itself | §7.2 |
| UX-039 | An explicit progress count, updating without reload | 6 Progress is explicit | §7.3 |
| UX-040 | Optimistic upload | 6 Upload behaviour | §7.4 |
| UX-041 | On failure the row reverts and shows the reason | 6 Upload behaviour | §7.4 |
| UX-042 | Accepted types and size stated before picking | 6 Upload behaviour | §7.4 |
| UX-043 | Removing a document returns to pending, visibly | 6 Upload behaviour | §7.4 |
| UX-044 | Never a full-page spinner after first load | 7 Loading and empty states | §8 |
| UX-045 | Request buttons spin and disable | 7 Loading and empty states | §8 |
| UX-046 | Empty states say what to do next | 7 Loading and empty states | §8 |
| UX-047 | Every possibly-empty list has a written empty state | 7 Loading and empty states | §8 |
| UX-048 | Not doing: tooltips on every field | 8 Not doing | §9 |
| UX-049 | Not doing: onboarding tour | 8 Not doing | §9 |
| UX-050 | Not doing: toasts for every action | 8 Not doing | §9 |
| UX-051 | Not doing: confirmation modals | 8 Not doing | §9 |
| UX-052 | Not doing: entrance animations, reveals, shimmer | 8 Not doing | §9 |
| UX-053 | Not doing: dark mode toggle | 8 Not doing | §9 |
| UX-054 | Not doing: autosave on the simulator | 8 Not doing | §9 |
| UX-055 | Done: computed result on first paint | 9 Definition of done | §10 |
| UX-056 | Done: input change never blanks the previous result | 9 Definition of done | §10 |
| UX-057 | Done: quotiteit chip is informational | 9 Definition of done | §10 |
| UX-058 | Done: sign-up lands on a prefilled application | 9 Definition of done | §10 |
| UX-059 | Done: a mid-wizard refresh loses nothing after step 1 | 9 Definition of done | §10 |
| UX-060 | Done: every checklist row uploads and explains itself | 9 Definition of done | §10 |
| UX-061 | Done: the flow completes at 375px | 9 Definition of done | §10 |

# Appendix B — What this spec implements

Most of this document is the visible face of rules already written down. These links are the reason
a UX change can never quietly contradict the domain.

| UX | Implements |
|---|---|
| UX-010 simulator prefill | `0-business-logic.md` AC-003 — the same six inputs |
| UX-017, UX-057 quotiteit chip | DOM-016, ERR-006 — above the norm is a flag, never an error |
| UX-018 region and first-home are primary | SIM-013, AC-005 — the €30,000 difference |
| UX-023 messages from error codes | ERR-002, `1-code-quality.md` CQ-063 |
| UX-027, UX-028 claiming a simulation | DOM-025 – DOM-027, `2-architecture.md` ARC-017 |
| UX-037, UX-038 the derived checklist | DOC-005 – DOC-009 |
| UX-039 completion without reload | APP-003 |
| UX-042 accepted types and size | DOC-001, DOC-002 |
| UX-043 removal returns to pending | APP-004, ARC-018 |
| UX-013, UX-045 no component calls HTTP itself | ARC-021, ARC-022 |
