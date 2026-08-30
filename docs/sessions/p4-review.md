# P4 — integration and final validation

T32 (the `VAL-027` manual run), T33 (read every diff) and T34 (the gate). Written during the run
rather than after it, so what follows is what was actually found, in the order it was found.

The run was made against the **production image** on `http://localhost:8080` — `docker build -f
infra/Dockerfile` plus `docker run` with a volume — rather than the deployed URL. `AI-001` puts
classification after a working deployment and T31 satisfied that early; this pass gates the *next*
deploy, so the artefact it exercises is the one about to be pushed. Two `VAL-027` steps needed
restating for that; both are recorded in `7-validation.md` Appendix B rather than quietly swapped.

---

## The one that mattered

**The production container served every JavaScript bundle as `index.html`, and so did the deployed
app.** `curl` on the bundle named by the page's own `<script src>` returned `200` with
`text/html`, the browser refused it on the module MIME check, and the page rendered as an empty
white screen. Every visitor to the deployed URL got that.

The cause: Angular's application builder emits `main-<hash>.js` and `styles-<hash>.css` at the
**root** of `dist/borrower-portal/browser`, not under `assets/`. `main.py` mounted `StaticFiles` at
`/assets` — a directory that is never created — and registered a catch-all that returned the shell
for everything else. The mount never matched anything, the catch-all matched the bundles, and every
response was a `200`, so nothing anywhere looked like a failure.

Why nothing caught it:

- `make e2e` runs Playwright against `ng serve`, which serves its own bundles. The production image
  is never exercised by any test.
- `tests/test_spa.py` had three tests. All three checked the fallback path — a deep route returns
  the shell, `/health` still resolves, an unknown `/api` route 404s. None checked that a file that
  *was* built comes back as itself. The suite was green over a completely broken artefact.

Fixed by moving the decision into `app/core/spa.py`: if the path names a file inside the build
output, return that file; otherwise return the shell. `/assets` mount deleted — it was dead. Two
tests added, one of which fails against the old behaviour.

---

## T32 · the eighteen steps

Every step run in a 375px window, in a real browser, reading screenshots rather than DOM assertions.

| Step | Result |
|---|---|
| 1–3, 5–7 | Pass. Brussels at €150 000 gives €0,00 duty, not negative; the first-home toggle moves cash by exactly €30 000; a 0% rate still computes €900,00. |
| **4** | **Failed.** Contribution equal to the price passes every client-side validator — only the server knows a loan of zero is not a loan. The 422 was swallowed by the `catchError` added at T45 and *nothing* appeared: the borrower saw the previous result sitting there with no explanation. The T45 fix that stopped a failed request killing the subscription had also removed the last path by which a server error reached the screen. Fixed: the page keeps the `{code, message, field}` body and the form renders it beside the field the response named (`UX-023`, `UX-024`). |
| 8–10 | Pass. Prefill, refresh and browser-back all hold. |
| **11** | **Failed, structurally.** "Change employment type and confirm the checklist changes" was impossible: the wizard renders for `DRAFT` only, so after submission there was no way back to the answers the checklist is derived from. A borrower who picked the wrong employment type was stuck with the wrong list permanently. The API had always allowed the PATCH. Fixed with a **Your answers** editor under the checklist. |
| 12–13 | Pass. A `.txt` renamed `.pdf` is rejected 415 on magic bytes, with the message beside its row. |
| **14** | Pass, after re-running it properly. The first attempt only had one of six documents, so there was no `DOCUMENTS_COMPLETE` to move back *from*; filling all six and removing one gives `6 of 6 "Documents complete" → 5 of 6 "Documents pending"`. |
| **15** | Half-failed. The API answered `404` with the right body, but the page rendered *nothing* — a header over white — because the template had no branch for a missing application. Fixed with an explicit "Application not found" state. |
| 16 | Pass. `/login?redirect=…` and back to the target URL. |
| **17** | Pass. `docker restart`, then still signed in, five documents still listed, and the first one still downloads as `%PDF…` with `Content-Disposition: attachment`. |
| 18 | The whole run was at 375px. The header wrapped onto a second line there — the 56px band of `UI-055` grew with it — and was fixed. |

---

## T33 · reading the source

All of `backend/app` and `frontend/src` in full; test diffs sampled per merge commit.

### Fixed

**The applications list always said "0 of 6 required documents uploaded."** `applications/router.py`
called `service.list_for_user(..., {})` — an empty map — because `applications` may not query the
documents table (`ARC-009`). Every row of "My applications" showed `documents_satisfied: 0` however
many were uploaded, while the detail page for the same application said *Documents complete*. Fixed
by moving `GET /api/applications` into `documents/router.py`, the precedent the checklist route
already set for exactly this reason (`2-architecture.md` §5.1). Regression test added; no test had
ever listed an application that had documents.

**The documents router was the only one breaking the controller rule.** `upload_document` had three
statements and built the service's input object field by field; `download_document` shaped an HTTP
response inline. `CQ-018` forbids both without exception. Reading the multipart body moved into a
dependency (`CQ-019`'s "input" row) and the attachment into a named helper — the same carve-out
`auth/router.py` already makes for the session cookie. Both handlers are now one statement.

**The review step read raw enums.** The last screen before submission printed `FLANDERS` and
`EMPLOYEE`. The region labels existed in two other places already, so the fix was one definition in
`core/labels.ts` that all three now import — the same reason `STATUS_CHIPS` was extracted at T63.

**Smaller things.** `main.py`'s docstring still said it knew about no domains ("at T02"). A
`# type: ignore` was holding up `Document.uploaded_at` while `None` was passed through it. The
emptiness rule for a proposal was written twice, in the pipeline and on the read side. `base64` and
`file_type` were imported inside function bodies for no reason. `RateLimiter.reset`'s docstring
claimed it ran after a successful login; nothing calls it, and it should not — clearing the window
on success would let one valid credential reset an attacker's budget.

### Explained and left alone

**`Provenance.DOCUMENT` has no live path.** Everything written to the financial profile is recorded
`MANUAL`, including a figure the borrower accepted from a document's proposal — because accepting
fills the form and they still press save, so what arrives is what they submitted. Writing `DOCUMENT`
would mean either trusting the client to assert its own provenance (which defeats the point of an
audit trail) or letting `applications` read the documents table to verify the claim (`ARC-009`
forbids it). Both docstrings now say this instead of saying the feature "does not exist yet".

**`borrower.monthly_net_income` is captured and never read.** The affordability assessment reads
`FinancialProfile` instead, because `API-037` replaces the borrower collection wholesale on every
PATCH. `DOM-023` records the supersession, so it is documented rather than dangling — but the
borrower is still asked for their income twice, in two places, and only the second one counts. Left
**Fixed after the walkthrough**, when the borrower hit it themselves: the wizard no longer asks.
The field stays on the wire and on the row — dropping a column is a migration, not a correction —
but nothing collects it any more, and the question is asked once, where the answer counts.

**`auth.interceptor.ts` passes every request through unchanged.** A structural placeholder that
`ARC-020`'s tree calls for, and its docstring says so. Kept.

---

## T34 · the gate

`make lint`, `make test` and the Tier-1 coverage command, run after the last fix rather than before
it. The twenty Tier-2 classifier tests stay skipped: `ANTHROPIC_API_KEY` is unset, which is the
correct default and not a gap (`AI-039` — the product works end to end with the flag off).

## Plumbing corrected along the way

The repository-root `.env` that `.env.example` is a template for reached **nothing**. Compose reads
its own `.env` from the compose file's directory (`infra/`), and `core/config.py` declares no
`env_file` — deliberately, since `DEP-023` keeps a file from being a legitimate production source of
secrets. So `ANTHROPIC_API_KEY` placed exactly where the example says to put it was silently ignored
in every local run. `infra/docker-compose.yml` now names `../.env` explicitly (`required: false`),
and `make backend` sources it for the one process it starts.
