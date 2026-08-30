# Spec conformance audit

Run after P4 and after the deploy, on `master` at the commit that is live on
`oper-credits-borrower-portal.fly.dev`. The tree audited is green: `ruff`, `mypy --strict`,
**407** backend tests (20 live classifier tests skipped, no key in the test environment), 33 vitest,
13 Playwright, and Tier-1 coverage at 100%.

The question is not "does it run" — P4 answered that. It is **"does it do what the specs say"**.
Ten documents, **673 unique requirement ids**, of which **389** are cited somewhere in code or
tests. This audit changes no code.

Audited in three tiers by risk rather than by document order: the rules a machine can settle, then
the numbers, then the 284 ids nothing in the codebase mentions.

---

## Verdict

**No critical divergence.** Every hard rule holds, every fixed number matches the spec to the cent,
and the three cross-domain edges are exactly the three that are declared.

Three things are declared and **not delivered**, all in the optional classifier, one of them
user-visible. Four more are cosmetic drift between spec text and code. Details below.

---

## Tier 1 — the rules a machine can settle

`CLAUDE.md` calls these defects rather than style disagreements, and notes that no linter checks
most of them. Every one was checked; every one holds.

| Rule | Result |
|---|---|
| `CQ-017`, `CQ-018` the controller rule | **Clean.** Every route handler in all four routers plus `main.py`, parsed with `ast`: exactly one statement, no `if`/`for`/`while`/`try`. |
| `CQ-021` no `Any` in `app/` | **Clean.** Two hits, both prose inside docstrings. |
| `CQ-014`, `CQ-027` money never `float` | **Clean.** No `float(` on any money path; TypeScript money is `string` throughout. |
| `CQ-093` SQL only in `repository.py` | **Clean.** No `select(`/`insert(` outside one. The `sqlalchemy` imports elsewhere are `AsyncSession` type annotations — the session is injected and passed down, which is `CQ-090` working as designed. |
| `ARC-012` `core` never imports `domains` | **Clean.** Zero. |
| `ARC-013`, `CQ-048` pure modules | **Clean.** All six import only stdlib, `decimal` and their own entities; none is `async`. |
| `ARC-016` – `ARC-019` cross-domain edges | **Clean on the boundary** — exactly three arrows, no fourth. See *Cosmetic 1* for the method lists. |
| `CQ-058` – `CQ-062` error handling | **Clean, with one documented exception.** Zero bare `except`. Four `except Exception`, three of which re-raise something more specific. The fourth is the background classifier, which `AI-023` *requires* to swallow — see *Cosmetic 2*. |
| `CQ-036` – `CQ-038` function limits | **Clean.** Nothing over the hard 50-line limit; nothing over four positional parameters. Two over the soft 30: `documents.service.upload` (42) and `pipeline.run` (39). |
| `ARC-040` three model files per domain | **Clean.** All four domains carry `tables.py`, `entities.py`, `schemas.py`. |
| `UI-027` – `UI-031`, `UI-064` | **Clean.** No component stylesheet has content, no `[ngStyle]` or `style=`, no hex outside `core/theme/`, and the only `@apply` sits inside `@layer base` where `UI-028` permits it. |
| `ARC-021`, `ARC-025` | **Clean.** No component or page touches HTTP — the only matches are `.spec.ts` test setup. `shared/` imports no domain. |
| `ARC-022` components inject nothing | **One borderline.** `simulation-form.component.ts:92` injects `DestroyRef` — an Angular lifecycle primitive for `takeUntilDestroyed`, not a service or a domain dependency. Judged conforming; noted so a reviewer is not surprised. |

## Tier 2 — the numbers

Every constant the specs fix by value was read out of the spec and compared to the code.

**All match.** Registration duty: Flanders 12% / 2%, Wallonia 12.5% / 3%, Brussels 12.5% with a
€200 000 *abattement* implemented as an allowance and not approximated as a reduced rate, which is
what `SIM-012` explicitly demands. Notary €3 300, dossier €350, valuation €285, mortgage costs
1.2%. Supervisory norm 0.90, compared **strictly greater** as `API-020` words it. DSTI bands 0.33 /
0.40; residual floor 1200 + 400 per extra adult + 300 per dependant, comfortable at ×1.10.
Classifier thresholds 0.60 and 0.85. Rate limit 10 attempts per 300 seconds. Upload cap 10 MB.
Password floor 10 characters.

Every figure in `AC-001` – `AC-009` is asserted literally in a test — `1152.95`, the `1165.57`
counter-example, `0.00443996`, `270000.00`, `0.9000`, `1414.52`, `424356.04`, `154356.04`,
`43175.00`, the whole six-row regional matrix, `0.0414` — with one exception:

- **`AC-005`'s second figure, `73175.00`, is not asserted anywhere.** The test asserts that the
  *difference* between the two tax statuses is exactly `30000.00`, and `43175.00` is pinned by the
  API test, so the second figure is entailed rather than absent. Sharper than the spec in one way
  (it tests the claim `SIM-013` actually makes) and weaker in another (both sides could drift
  together). Verified by hand during T32: `€ 43.175,00 → € 73.175,00`. **No action needed.**

## Tier 3 — declared but never mentioned

284 ids appear in no source file. Most are prose, rationale, or statements about the specs
themselves, and the behaviour-bearing ones were checked individually. Three are genuinely not
delivered.

### Not delivered

**1. `AI-027` — the classification result does not appear without a manual refresh.** *(the one
that matters)*

> "`PENDING` renders as a subtle spinner on the row… The frontend polls the checklist once, three
> seconds after an upload, and stops."

Neither half exists.

- `ClassificationStatus.PENDING` is defined in `pipeline.py` and **never written**: the pipeline
  writes `DONE` or `FAILED` only, so the state is unreachable and there is nothing for a spinner to
  render. The three `PENDING` matches in the frontend are all `DOCUMENTS_PENDING`, the application
  status, which is unrelated.
- `onFileSelected` calls `refreshChecklist()` once, **immediately**
  (`application-wizard.component.ts:173`). The classification runs in a background task *after* the
  201, so at that moment there is nothing to fetch. There is no second read.

The consequence is exactly what a borrower sees today: upload a payslip, the row closes instantly,
and the message and the proposal appear only after reloading the page by hand. During this session
that was worked around in conversation — "refresh if it is empty" — without either of us noticing
the spec had already called for the fix.

*Cost to close:* small. One `setTimeout(() => this.refreshChecklist(), 3000)` after a successful
upload, plus writing `PENDING` when the task is queued and rendering it. The spec's "once, then
stop" is deliberate and should be kept — no polling loop, no websocket.

**2. `AI-041` — a confident mismatch has no "keep it anyway" action.**

> "A confident mismatch shows a warning with a 'keep it anyway' action."

The warning is rendered — a real Opus 5 answer, composed server-side, verified live in this
session. The explicit action does not exist anywhere in the frontend. The row is satisfied either
way, so the action would be an acknowledgement that dismisses the warning rather than a state
change; the borrower is not blocked. `AI-006`'s substance — the model advises, the borrower decides
— holds. **Declared and not built.**

*Cost to close:* small, but it needs a decision first — dismissal is per-document UI state, and
where it lives (a column, or nothing at all) is a design question rather than a bug fix.

**3. `APP-005` — `DOCUMENTS_COMPLETE → UNDER_REVIEW` has no trigger.**

The transition is legal in the state machine and no code performs it: there is no back-office, and
nothing in the borrower-facing product should advance a file into review. Recorded through
`APP-010` and `SCP-018`, which name `UNDER_REVIEW` as a collapsed stand-in for three real-world
gates. **Deliberate and recorded — no action.**

### Verified present despite never being cited

Spot-checked rather than assumed: `API-007` timestamps do carry the `Z` suffix
(`2026-08-30T20:41:06.789345Z` — an earlier impression to the contrary came from reading SQLite
directly, not the API); `API-020` compares strictly; `AUTH-013`/`AUTH-016` (HS256, 24h),
`AUTH-051` (unique index plus `IntegrityError` mapping), `AUTH-052` (httpOnly, SameSite=Lax, Secure
outside development), `AUTH-054` (startup fails on a short secret), `AUTH-055` (`verify_against_
nobody` equalises timing), `AUTH-056`/`API-065`/`API-077` (404, never 403), `ERR-004` (413 for an
oversized upload), `DOM-011` (contribution below price, verified in the browser at T32),
`API-057`/`API-058` (both probes). `SCP-*` are the deliberate cuts and each is stated as such.

### Not audited id-by-id

`UI-*` and `UX-*` — 77 uncited ids, almost all visual or behavioural claims. They were exercised
through the 18-step `VAL-027` walkthrough at 375px, the 13 Playwright scenarios and the screenshot
passes in both themes, but not walked one id at a time. Nothing observed contradicts them; this is
stated as a limit of the audit rather than a clean bill.

---

## Cosmetic drift

1. **`ARC-018` and `ARC-047` name fewer methods than the code calls.** The arrows are right and
   there is no fourth, but `ARC-047` says `simulation.service.get()` while the code uses
   `get_stored`, `monthly_payment_for` and — since T32 — `claim_for_user`; `ARC-018` names
   `recompute_status()` and `checklist()` while the code also uses `get_owned`, `ids_for_user` and
   `list_for_user`. Two of those widenings are recorded elsewhere (`10-implementation.md`, the
   service docstrings, `p4-review.md`); the spec section that exists specifically so nobody invents
   a fourth edge should list them.
2. **`CQ-060`/`CQ-061` have no carve-out for the background task.** "Never log and swallow" and
   "never `except Exception` without re-raising" are absolute in `1-code-quality.md`, while
   `AI-023` requires `pipeline.run` to do exactly that — it runs after the response, so there is
   nobody left to raise to. The business spec wins per `CLAUDE.md`, and the code is right; the
   quality spec should name the exception so a reviewer does not flag it as a defect.
3. **`styles.css:76` cites `UI-025` for the `@apply` carve-out; the rule is `UI-028`.**
4. **`AC-005` records two absolute figures where the test pins one absolute and the delta.** Either
   the criterion or the test could move; the test is arguably the better claim.

---

## Worth making permanent in `make lint`

Several of this session's defects survived because "no linter expresses them" was treated as the
end of the sentence. These checks are cheap, and each one is a rule the specs already call
load-bearing:

- **the controller rule** — the `ast` walk used above is ten lines and settles `CQ-017`/`CQ-018`
  exactly;
- **cross-domain edges** — grep `self._<other-domain>.` in every `service.py` and compare against a
  declared list, so a fourth arrow fails the build instead of being noticed in review;
- **pure-module imports** — the import whitelist for the six `ARC-013` modules;
- **`Any` in `app/`**, restricted to annotations rather than prose;
- **`select(`/`insert(` outside `repository.py`**.

The two that would have caught real production failures are not in this list, and are worth more
than all of them: a test that fetches the built bundle from the production image and asserts its
content type, and a startup check that the database schema matches the metadata. The first now
exists (`tests/test_spa.py`); the second is now enforced at startup rather than tested.
