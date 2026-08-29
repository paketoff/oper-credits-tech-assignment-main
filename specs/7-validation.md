---
id: VAL
title: Validation & Edge Cases
status: draft
version: 1.0.0
owner: paketoff
updated: 2026-08-29
---

# 7 — Validation & Edge Cases

Companion to [`0-business-logic.md`](0-business-logic.md) (invariants and acceptance criteria) and
[`4-ux.md`](4-ux.md) (when validation fires).

This document has two jobs. It is the specification for validation rules, and it is the **manual test
plan run before submission**. The brief states the reviewer will try edge cases. Every row in §5
should therefore have defined behaviour, not accidental behaviour.

## 1. Where validation lives

**VAL-001.** Three layers, three distinct jobs. Keeping them distinct is what stops rules from
drifting apart.

| Layer | Responsible for | Example |
|---|---|---|
| **Pydantic** | Shape: types, ranges, required fields, `extra="forbid"` | `term_months` is an int between 12 and 360 |
| **Domain** | Rules pydantic cannot express | Own contribution must be less than property value |
| **Frontend** | *When* to show a message, and mirroring constraints for UX | `min`/`max` on the input, error shown on blur |

**VAL-002. A rule is defined in exactly one place.** The frontend mirrors constraints so the borrower
gets immediate feedback, but it never decides validity. Error text always comes from the backend
error code, never from a hardcoded string in a template (`4-ux.md` UX-023).

**VAL-003. Corollary: a request that bypasses the frontend must be rejected identically. Anything
enforced only in the browser does not exist.**

## 2. Error codes

**VAL-004. This table is the registry.** One catalogue, used by backend and frontend. Codes are
stable strings; messages may change. `1-code-quality.md` CQ-063 and `0-business-logic.md` ERR-002
both point here — a code that is not in this table does not exist.

| Code | HTTP | Message | Raised by |
|---|---|---|---|
| `VALIDATION_ERROR` | 422 | Check the highlighted fields. | Pydantic, via the handler |
| `LOAN_AMOUNT_NOT_POSITIVE` | 422 | Your own contribution must be less than the property price. | Simulation domain |
| `TERM_OUT_OF_RANGE` | 422 | Term must be between 1 and 30 years. | Simulation domain |
| `RATE_OUT_OF_RANGE` | 422 | Interest rate must be between 0% and 20%. | Simulation domain |
| `PROPERTY_VALUE_OUT_OF_RANGE` | 422 | Property price must be between €10,000 and €10,000,000. | Simulation domain |
| `JKP_COMPUTATION_FAILED` | 500 | Could not compute the effective annual rate. | Calculator |
| `SIMULATION_NOT_FOUND` | 404 | Simulation not found. | Simulation repository |
| `EMAIL_ALREADY_REGISTERED` | 409 | That email is already registered. | Auth |
| `INVALID_CREDENTIALS` | 401 | Email or password is incorrect. | Auth |
| `NOT_AUTHENTICATED` | 401 | Please sign in. | Auth dependency |
| `TOO_MANY_ATTEMPTS` | 429 | Too many attempts. Try again in a few minutes. | Rate limiter |
| `APPLICATION_NOT_FOUND` | 404 | Application not found. | Application service |
| `INVALID_STATE_TRANSITION` | 409 | This application cannot move to that state. | State machine |
| `APPLICATION_ALREADY_SUBMITTED` | 409 | This application has already been submitted. | Application service |
| `UNSUPPORTED_DOCUMENT_TYPE` | 415 | Only PDF, JPEG and PNG files are accepted. | Document service |
| `DOCUMENT_TOO_LARGE` | 413 | Files must be under 10 MB. | Upload middleware |
| `DOCUMENT_EMPTY` | 422 | That file is empty. | Document service |
| `DOCUMENT_TYPE_NOT_REQUIRED` | 422 | That document is not part of this checklist. | Document service |
| `DOCUMENT_NOT_FOUND` | 404 | Document not found. | Document repository |
| `UPLOAD_READ_FAILED` | 500 | Upload failed. Please try again. | Document service |
| `STORAGE_UNAVAILABLE` | 503 | Storage is temporarily unavailable. | Repository — database unreachable, or the blob directory is not writable |
| `STORAGE_CORRUPT` | 500 | Stored data could not be read. | Repository — database integrity error, or a blob referenced by a row is missing from disk |

**VAL-005.** 422 is the default for an input violation (`ERR-001`), not a blanket. Three codes are
deliberately not 422: `JKP_COMPUTATION_FAILED` and `UPLOAD_READ_FAILED` are server-side failures, and
`INVALID_STATE_TRANSITION` and `APPLICATION_ALREADY_SUBMITTED` are conflicts, not bad input.

**VAL-006.** Error response shape, identical for every failure:

```json
{ "code": "LOAN_AMOUNT_NOT_POSITIVE", "message": "...", "field": "own_contribution" }
```

**VAL-007.** `field` is present when the error maps to one input, so the frontend can place the
message next to it rather than showing a toast. This is what makes `4-ux.md` UX-024 implementable.

## 3. Field rules

### 3.1 Simulation

**VAL-008.**

| Field | Rule | On violation |
|---|---|---|
| `property_value` | Decimal, 10 000 – 10 000 000, 2 dp | `PROPERTY_VALUE_OUT_OF_RANGE` |
| `own_contribution` | Decimal, ≥ 0, strictly < `property_value` | `LOAN_AMOUNT_NOT_POSITIVE` |
| `term_months` | int, 12 – 360 | `TERM_OUT_OF_RANGE` |
| `annual_nominal_rate` | Decimal, 0 – 0.20, 4 dp | `RATE_OUT_OF_RANGE` |
| `region` | enum: `FLANDERS`, `WALLONIA`, `BRUSSELS` | `VALIDATION_ERROR` |
| `is_first_home` | bool, required | `VALIDATION_ERROR` |

The ranges are the invariants `DOM-010` – `DOM-015`; this table is where the error code for each is
fixed.

**VAL-009.** `quotiteit` above 0.90 is **valid**. It returns `above_supervisory_norm: true` and is
never an error. Belgium has no statutory LTV cap; rejecting it would be a domain error on our side.
→ `DOM-016`, `ERR-006`.

### 3.2 Auth

**VAL-010.**

| Field | Rule |
|---|---|
| `email` | Normalised to lowercase and trimmed; basic RFC-shape check only |
| `password` | Minimum 10 characters. No composition rules. |
| `simulation_id` | Optional UUID. Invalid or unknown is ignored, never an error. |

→ `6-auth.md` AUTH-010, AUTH-023, AUTH-031.

### 3.3 Application

**VAL-011.**

| Field | Rule |
|---|---|
| `borrowers` | At least one; each requires `full_name`, `date_of_birth`, `employment_type` |
| `date_of_birth` | Age between 18 and 75 at submission (`DOM-028`) |
| `monthly_net_income` | Decimal ≥ 0, optional at draft, required at submit |
| `property.purchase_price` | Same range as `property_value` |
| `property.property_type` | enum: `EXISTING`, `NEW_BUILD` |

**VAL-012.** Draft steps validate only their own fields. Full validation runs once, on submit.
→ `UX-032`.

### 3.4 Documents

**VAL-013.**

| Rule | Value |
|---|---|
| Accepted types | `application/pdf`, `image/jpeg`, `image/png` |
| Maximum size | 10 MB |
| Minimum size | 1 byte |
| `doc_type` | Must appear in the application's computed checklist |
| Application state | Must not be `SUBMITTED` before documents open, nor `WITHDRAWN` |

→ `DOC-001`, `DOC-002`, `DOC-005`.

## 4. Number formatting

**VAL-014.** Belgian locale writes `300.000,50` — comma for decimals, dot for thousands.
`p-inputnumber` with `locale="nl-BE"` displays exactly that (`3-ui.md` UI-040).

**VAL-015. Only the canonical form crosses the wire: `"300000.50"`.**

- **VAL-016** — The frontend converts from display format to canonical before sending.
- **VAL-017** — **The backend never parses a localised number.** No comma-swapping, no
  thousands-separator stripping. Attempting it is how €300,000.50 silently becomes €300.50.
- **VAL-018** — Money is a JSON **string**, never a number. `0.1 + 0.2` in JavaScript is why.
  → `SIM-021`, `CQ-014`, `ARC-026`.
- **VAL-019** — Rates cross the wire as fractions: `"0.0400"`, not `"4.00"`. The percent sign belongs
  to display only.

## 5. Edge cases

**VAL-020.** Input, expected behaviour, code. This table is the manual test plan.

### 5.1 Simulation

| Input | Expected | Code |
|---|---|---|
| `own_contribution == property_value` | Rejected. Loan would be zero. | `LOAN_AMOUNT_NOT_POSITIVE` |
| `own_contribution > property_value` | Rejected | `LOAN_AMOUNT_NOT_POSITIVE` |
| `own_contribution == 0` | **Valid.** Quotiteit 100%, flagged above norm. | — |
| `annual_nominal_rate == 0` | **Valid.** Separate branch: `M = K / n`. No division by zero. | — |
| `annual_nominal_rate == 0.20` | Valid, upper bound inclusive | — |
| `annual_nominal_rate == 0.2001` | Rejected | `RATE_OUT_OF_RANGE` |
| `term_months == 11` | Rejected | `TERM_OUT_OF_RANGE` |
| `term_months == 361` | Rejected | `TERM_OUT_OF_RANGE` |
| Negative `property_value` | Rejected | `PROPERTY_VALUE_OUT_OF_RANGE` |
| 50-digit `property_value` | Rejected by pydantic `max_digits`, no overflow | `VALIDATION_ERROR` |
| `property_value` with 5 decimals | Rejected | `VALIDATION_ERROR` |
| Brussels, `property_value` = 150 000, first home | Registration duty is **exactly 0**. `max(0, price − 200 000)` — never negative. | — |
| Brussels, `property_value` = 200 000, first home | Registration duty exactly 0 | — |
| Unknown `region` string | Rejected | `VALIDATION_ERROR` |
| Extra field in the body | Rejected — `extra="forbid"` | `VALIDATION_ERROR` |
| `property_value` sent as a JSON number | Accepted by pydantic, but the frontend must send a string. Covered by a test. | — |
| Quotiteit exactly 0.90 | Valid, **not** flagged. The flag is `> 0.90`, not `>=`. | — |

### 5.2 Auth

| Input | Expected | Code |
|---|---|---|
| Signup with an existing email | Rejected | `EMAIL_ALREADY_REGISTERED` |
| Signup with `Test@Example.com` when `test@example.com` exists | Rejected — emails normalise to lowercase | `EMAIL_ALREADY_REGISTERED` |
| Password of 9 characters | Rejected | `VALIDATION_ERROR` |
| Login, unknown email | 401, same message and comparable timing as a wrong password | `INVALID_CREDENTIALS` |
| Login, wrong password | 401, identical response | `INVALID_CREDENTIALS` |
| 11 login attempts in 5 minutes | Rejected | `TOO_MANY_ATTEMPTS` |
| Signup with an unknown `simulation_id` | **Signup succeeds.** Claim silently skipped. | — |
| Signup with an already-claimed `simulation_id` | **Signup succeeds.** Simulation not reassigned. | — |
| Request to a protected route with no cookie | 401 | `NOT_AUTHENTICATED` |
| Request with a tampered token | 401. Signature check fails. | `NOT_AUTHENTICATED` |
| Request with an expired token | 401, frontend redirects to login preserving the target URL | `NOT_AUTHENTICATED` |
| Token expires mid-wizard | 401, redirect to login, **draft still on the server**, borrower returns to where they were | — |

### 5.3 Application

| Input | Expected | Code |
|---|---|---|
| Another user's application id | **404, not 403.** Existence is not confirmed. | `APPLICATION_NOT_FOUND` |
| Double submit (two clicks) | Idempotent. The second returns the same state, not an error. Button also disables while in flight. | — |
| Submit an already-submitted application | Rejected | `APPLICATION_ALREADY_SUBMITTED` |
| Submit with a required field missing | Rejected, `field` names the input | `VALIDATION_ERROR` |
| Refresh mid-wizard | Draft reloads from the server. Nothing lost after step 1. | — |
| Browser back button in the wizard | Returns to the previous step with data intact | — |
| Borrower aged 17 at submission | Rejected | `VALIDATION_ERROR` |
| Direct URL to a step of someone else's application | 404 | `APPLICATION_NOT_FOUND` |
| Change employment type after uploading payslips | Checklist recomputes. Uploaded documents are kept but may no longer be required; status recalculates. | — |

### 5.4 Documents

| Input | Expected | Code |
|---|---|---|
| `.exe` renamed to `.pdf` | Rejected. Magic-byte check, not extension. | `UNSUPPORTED_DOCUMENT_TYPE` |
| `.docx` upload | Rejected | `UNSUPPORTED_DOCUMENT_TYPE` |
| 100 MB file | Rejected at the ASGI layer, **before** the body is read into memory | `DOCUMENT_TOO_LARGE` |
| 0-byte file | Rejected | `DOCUMENT_EMPTY` |
| Filename `../../etc/passwd` | Sanitised. Stored under a generated key; the original name is never used as a path. | — |
| Filename with unicode or emoji | Accepted, stored as metadata only | — |
| `doc_type` not in this application's checklist | Rejected | `DOCUMENT_TYPE_NOT_REQUIRED` |
| Second upload of the same `doc_type` | Accepted. Both stored; the requirement stays satisfied. | — |
| Delete the last document satisfying a requirement | Application moves `DOCUMENTS_COMPLETE → DOCUMENTS_PENDING`. **Normal transition, not an error.** | — |
| Delete a document from another user's application | 404 | `DOCUMENT_NOT_FOUND` |
| Upload while offline | Row reverts, inline message, no silent failure | — |

### 5.5 Platform

| Input | Expected |
|---|---|
| Direct hit on `/application/123` | Angular shell served, route resolves. **Not a 404.** |
| Refresh on a deep route | Same |
| `fly apps restart` | Users, applications and documents survive — they are on the volume |
| `/data` unwritable | `/ready` returns 503; writes return `STORAGE_UNAVAILABLE`. `/health` still returns 200, because liveness must not depend on storage. |
| Database unreachable | `STORAGE_UNAVAILABLE`, 503, no stack trace to the client |
| Row references a blob missing from disk | `STORAGE_CORRUPT`, 500, no filesystem path in the response |
| Two simultaneous signups, same email | One succeeds, one gets `EMAIL_ALREADY_REGISTERED`. The unique index decides, not the pre-check. |
| Upload fails after the blob is written | Transaction rolls back. No orphan row. An orphan blob on disk is acceptable and is noted as a known gap. |

**VAL-021. Known gap:** the orphan blob above is never collected. The database stays consistent —
`CQ-091` puts the transaction boundary in the service — but a failed upload can leave bytes on disk
with no row pointing at them. A sweep job is the fix; at this scope the cost is a few kilobytes.

## 6. File validation detail

**VAL-022.** Extension and `Content-Type` are both client-controlled and neither is trustworthy.
Check the bytes. The detector is pure and lives in `domains/documents/file_type.py`
(`2-architecture.md` ARC-008).

```python
_MAGIC: dict[bytes, str] = {
    b"%PDF-": "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
}


def detect_content_type(head: bytes) -> str | None:
    """Identify a file from its leading bytes.

    Extension and client-supplied Content-Type are both attacker-controlled,
    so neither is used for the accept decision.
    """
    for signature, content_type in _MAGIC.items():
        if head.startswith(signature):
            return content_type
    return None
```

Roughly fifteen lines, and it turns "we check the extension" into "we check the file". In a fintech
review that difference is noticed.

Storage rules:

- **VAL-023** — The stored key is generated (`{application_id}/{uuid4}`). The original filename is
  metadata only and never touches a filesystem path. → `DOC-003`.
- **VAL-024** — The size limit is enforced by ASGI configuration, so an oversized body is rejected
  before it is buffered into memory.
- **VAL-025** — Files are served through an authenticated endpoint that re-checks ownership, never as
  static files. Blobs are not the static files on the public route list (`6-auth.md` AUTH-039); the
  ownership rule is AUTH-034.

## 7. Not validated, deliberately

**VAL-026.**

| Not validated | Why |
|---|---|
| Deep email format checking | RFC 5322 in a regex is a well-known trap. A basic shape check plus a verification email is the correct answer, and email is stubbed per the brief. |
| Whether the address or property exists | Needs a cadastral integration. Out of scope. |
| Whether the price is plausible for the market | Needs a valuation model. Out of scope, and noted as `SCP-014`. |
| Whether an uploaded document is what it claims to be | This is what an extraction model does. It is the natural next step and the domain's real pain point (`SCP-015`). |
| Password strength beyond length | Composition rules reduce entropy in practice and annoy users. Length is what matters (`AUTH-010`). |

## 8. Pre-submission manual run

**VAL-027.** Fifteen minutes, on the deployed URL, on a phone-width window. Half of these are faster
to check by hand than to write a test for.

1. Open the app cold. **A result is already on screen.** No interaction needed.
2. Change the property price. The old figures stay visible while the new ones compute; nothing jumps.
3. Set own contribution to 0. Quotiteit reads 100%, the above-norm chip appears, no error.
4. Set own contribution equal to the price. A clear error appears next to that field.
5. Switch region to Brussels with a price of 150 000. Registration duty is 0, not negative.
6. Toggle first home in Flanders. Cash needed moves by €30,000 on a €300,000 property.
7. Set the rate to 0. A payment is still computed.
8. Sign up. Land on an application **prefilled from the simulation**.
9. Fill step 1, refresh the page. Nothing is lost.
10. Use the browser back button. The previous step still holds its data.
11. Reach documents. Change employment type and confirm the checklist changes.
12. Upload a PDF. The row turns satisfied and the count increases.
13. Upload a `.txt` renamed to `.pdf`. Rejected with a clear message.
14. Delete the document. The application moves back to pending, visibly.
15. Open a random UUID application URL. 404, not 403, no stack trace.
16. Log out, then hit a protected URL. Redirected to login; after logging in, land on the target URL.
17. `fly apps restart`, then reload. Still logged in, application still there, uploaded documents
    still listed and still downloadable.
18. Run the whole flow once at 375px width.

## 9. Definition of done

- **VAL-028** — Every code in §2 is raised by real code and rendered by the frontend.
- **VAL-029** — Every row in §5 behaves as written.
- **VAL-030** — No error response contains a stack trace or a filesystem path.
- **VAL-031** — No validation rule exists only in the browser.
- **VAL-032** — Every uniqueness rule is backed by a database constraint, not only by an
  application-level check.
- **VAL-033** — The §8 run passes on the deployed URL before the link is sent.

---

# Appendix A — Traceability

Source: `09-validation.md`, superseded by this document.

| ID | Statement | Source § | § |
|---|---|---|---|
| VAL-001 | Three validation layers with distinct jobs | 1 Where validation lives | §1 |
| VAL-002 | A rule is defined in exactly one place | 1 Where validation lives | §1 |
| VAL-003 | Browser-only enforcement does not exist | 1 Where validation lives | §1 |
| VAL-004 | The 22-code registry | 2 Error codes | §2 |
| VAL-005 | 422 is a default, not a blanket | added — resolves the CQ-063 status conflict | §2 |
| VAL-006 | The error response shape | 2 Error codes | §2 |
| VAL-007 | `field` places the message next to its input | 2 Error codes | §2 |
| VAL-008 | Simulation field rules and their codes | 3 Field rules | §3.1 |
| VAL-009 | Quotiteit above 0.90 is valid, never an error | 3 Field rules | §3.1 |
| VAL-010 | Auth field rules | 3 Field rules | §3.2 |
| VAL-011 | Application field rules | 3 Field rules | §3.3 |
| VAL-012 | Draft validates its own step; full validation on submit | 3 Field rules | §3.3 |
| VAL-013 | Document rules | 3 Field rules | §3.4 |
| VAL-014 | Belgian display format is `300.000,50` | 4 Number formatting | §4 |
| VAL-015 | Only the canonical form crosses the wire | 4 Number formatting | §4 |
| VAL-016 | The frontend converts before sending | 4 Number formatting | §4 |
| VAL-017 | The backend never parses a localised number | 4 Number formatting | §4 |
| VAL-018 | Money is a JSON string, never a number | 4 Number formatting | §4 |
| VAL-019 | Rates cross as fractions, not percentages | 4 Number formatting | §4 |
| VAL-020 | The 57 edge cases | 5 Edge cases | §5 |
| VAL-021 | Known gap: the orphan blob is never collected | 5 Edge cases | §5.5 |
| VAL-022 | Magic-byte detection, not extension or Content-Type | 6 File validation detail | §6 |
| VAL-023 | Generated storage key; filename is metadata only | 6 File validation detail | §6 |
| VAL-024 | Size limit enforced at the ASGI layer | 6 File validation detail | §6 |
| VAL-025 | Blobs served through an authenticated endpoint | 6 File validation detail | §6 |
| VAL-026 | Five things deliberately not validated | 7 Not validated | §7 |
| VAL-027 | The 18-step pre-submission run | 8 Pre-submission manual run | §8 |
| VAL-028 | Done: every code is raised and rendered | 9 Definition of done | §9 |
| VAL-029 | Done: every §5 row behaves as written | 9 Definition of done | §9 |
| VAL-030 | Done: no stack trace or path in a response | 9 Definition of done | §9 |
| VAL-031 | Done: no browser-only rule | 9 Definition of done | §9 |
| VAL-032 | Done: uniqueness backed by a constraint | 9 Definition of done | §9 |
| VAL-033 | Done: the §8 run passes on the deployed URL | 9 Definition of done | §9 |

# Appendix B — Corrections and additions against the source

| Item | Resolution |
|---|---|
| `JKP_COMPUTATION_FAILED` 500, `INVALID_STATE_TRANSITION` 409, `UPLOAD_READ_FAILED` 500 | This spec's statuses win. `CQ-063` had them at 422, inferred from `ERR-001`'s default; VAL-005 records why they are exceptions. |
| `property_value` 10 000 – 10 000 000 | The range was narrower than `DOM-010` (`> 0`). The invariant moved into the business spec — see `DOM-010` — and this table references it. |
| Borrower age 18 – 75 at submission | Existed in no spec. Added as `DOM-028`. |
| `00-scope.md`, `01-domain.md`, `02-simulation.md`, `06-ux.md` references | Rewritten to `0-business-logic.md` and `4-ux.md` |
