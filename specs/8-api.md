---
id: API
title: API
status: draft
version: 1.0.0
owner: paketoff
updated: 2026-08-29
---

# 8 — API

The wire contract. **This is what unblocks the frontend:** work unit C can start as soon as this
document is fixed, without waiting for the backend implementation — which is exactly what
`2-architecture.md` ARC-029 means by "the contract, not the implementation, is the unblocker".

Companion to [`0-business-logic.md`](0-business-logic.md) (entities and the numbers),
[`6-auth.md`](6-auth.md) (sessions) and [`7-validation.md`](7-validation.md) (error codes).

## 1. Conventions

Plain REST. There is nothing clever here, and there should not be.

- **API-001** — All routes are prefixed `/api`. `/health`, `/ready` and the static files are not.
- **API-002** — `snake_case` on the wire, matching the pydantic schemas and the TypeScript models. No
  renaming layer in either direction (`2-architecture.md` ARC-027, `1-code-quality.md` CQ-013).
- **API-003** — Path identifiers are UUID4.
- **API-004** — **Money is a JSON string**, always with two decimals: `"300000.00"`. Never a number.
  `0.1 + 0.2` in JavaScript is why. → `SIM-021`, `CQ-014`, `ARC-026`.
- **API-005** — **Rates are fractions as strings**, four decimals: `"0.0400"` is 4%. The percent sign
  belongs to display only. → `VAL-019`.
- **API-006** — **Ratios are fractions as strings**, four decimals: `"0.9000"` is a 90% quotiteit.
- **API-007** — Timestamps are ISO 8601 UTC with a `Z` suffix.
- **API-008** — Only canonical number formats cross the wire. The backend never parses a localised
  number; see `7-validation.md` §4.
- **API-009** — No trailing slashes.

### 1.1 Three departures from reflex REST, and why

**API-010. The checklist is a sub-resource, not a field on the application.**
`GET /api/applications/{id}/checklist`. It is derived and it changes whenever a document is uploaded
or an employment type changes. Embedding it in the application body would force the frontend to
refetch the whole application to refresh a list.

**API-011. State changes are actions, not a PATCH on `status`.**
`POST /api/applications/{id}/submit`, not `PATCH {"status": "SUBMITTED"}`. This is not aesthetics: if
status is an ordinary writable field, any client can set any value and the state machine is bypassed.
The transition belongs to the domain and is validated inside it (`APP-009`).

**API-012. Simulations are created with POST and persisted.**
A `GET` with query parameters would be tempting for a pure calculation. It does not work: an
anonymous simulation has to be claimable at signup, so it needs an identity and it has to exist.
→ `DOM-025` – `DOM-027`, `AUTH-030`.

## 2. Error shape

**API-013.** Every failure of an `/api` route, without exception:

```json
{
  "code": "LOAN_AMOUNT_NOT_POSITIVE",
  "message": "Your own contribution must be less than the property price.",
  "field": "own_contribution"
}
```

**API-014.** `field` is present only when the error maps to a single input, so the frontend can render
it beside that input instead of as a toast. Codes are the full catalogue in `7-validation.md` §2
(VAL-004); the shape is VAL-006 and VAL-007.

**API-015.** Validation errors from pydantic are normalised into the same shape by the global
exception handler. A raw FastAPI `detail` array never reaches the client.

**API-069.** `/health` and `/ready` are outside this contract, because they are outside `/api`
(API-001). They are platform probes read by Fly, not by the frontend, and they answer
`{"status": ...}` with 200 or 503 — never `{code, message, field}`. This is the only carve-out, and
it exists because the reader is a health checker rather than a client.

## 3. Endpoints

**API-016.**

| Method | Path | Auth |
|---|---|---|
| POST | `/api/simulations` | public |
| GET | `/api/simulations/{id}` | public |
| POST | `/api/auth/signup` | public |
| POST | `/api/auth/login` | public |
| POST | `/api/auth/logout` | public |
| GET | `/api/auth/me` | session |
| GET | `/api/applications` | session |
| POST | `/api/applications` | session |
| GET | `/api/applications/{id}` | session |
| PATCH | `/api/applications/{id}` | session |
| POST | `/api/applications/{id}/submit` | session |
| GET | `/api/applications/{id}/checklist` | session |
| POST | `/api/applications/{id}/documents` | session |
| GET | `/api/applications/{id}/documents/{document_id}` | session |
| DELETE | `/api/applications/{id}/documents/{document_id}` | session |
| GET | `/health` | public |
| GET | `/ready` | public |

**API-017.** Every session route resolves the user from the cookie and scopes the query by `user_id`.
A resource owned by someone else returns **404, not 403** (`AUTH-035`, `ERR-005`).

## 4. Simulations

### `POST /api/simulations` → 201

**API-018.**

```json
{
  "property_value": "300000.00",
  "own_contribution": "30000.00",
  "term_months": 300,
  "annual_nominal_rate": "0.0400",
  "region": "FLANDERS",
  "is_first_home": true
}
```

```json
{
  "id": "8f1c...",
  "loan_amount": "270000.00",
  "quotiteit": "0.9000",
  "above_supervisory_norm": false,
  "monthly_payment": "1414.52",
  "total_paid": "424356.04",
  "total_interest": "154356.04",
  "nominal_rate": "0.0400",
  "jkp": "0.0414",
  "upfront": {
    "registration_duty": "6000.00",
    "notary_fee": "3300.00",
    "mortgage_costs": "3240.00",
    "dossier_fee": "350.00",
    "valuation_fee": "285.00",
    "total_costs": "13175.00",
    "own_contribution": "30000.00",
    "total_cash_needed": "43175.00"
  },
  "created_at": "2026-08-30T09:12:44Z"
}
```

**API-019.** These figures are the acceptance criteria `AC-003` and must match to the cent.

**API-020.** `above_supervisory_norm` is `quotiteit > 0.90`, strictly greater. It is informational and
never an error. → `DOM-016`, `VAL-009`.

### `GET /api/simulations/{id}` → 200

**API-021.** Same body. Public: the id is an unguessable UUID and the payload contains no personal
data. Used by the frontend to restore a simulation after signup.

**API-022.** 404 `SIMULATION_NOT_FOUND` if it does not exist.

## 5. Auth

Full behaviour in [`6-auth.md`](6-auth.md). Contract only here.

### `POST /api/auth/signup` → 201

**API-023.**

```json
{ "email": "test@example.com", "password": "hunter2hunter2", "simulation_id": "8f1c..." }
```

```json
{
  "user": { "id": "3a9e...", "email": "test@example.com", "created_at": "..." },
  "claimed_simulation_id": "8f1c..."
}
```

**API-024.** Sets the `session` cookie. `claimed_simulation_id` is `null` when the id was missing,
unknown or already owned — **none of which fail the request** (`AUTH-031`).

**Signup does not create an application**, and returned an `application_id` until T17. Creating one
would make `auth.service` call a second foreign domain, and `2-architecture.md` §5.1 explains why
the boundary moved instead of the edge count. The client calls `POST /api/applications` next, which
is what that endpoint has always been for.

**API-025.** 409 `EMAIL_ALREADY_REGISTERED`.

### `POST /api/auth/login` → 200

**API-026.**

```json
{ "email": "test@example.com", "password": "hunter2hunter2" }
```

Returns the same `user` object and sets the cookie. 401 `INVALID_CREDENTIALS` for both an unknown
email and a wrong password, with identical message and comparable timing (`AUTH-025`, `AUTH-026`).

### `POST /api/auth/logout` → 204

**API-027.** Clears the cookie. Succeeds whether or not a session existed.

### `GET /api/auth/me` → 200

**API-028.** Returns the `user` object, or 401 `NOT_AUTHENTICATED`. The frontend calls this on boot
because it cannot read the httpOnly cookie itself (`AUTH-029`).

## 6. Applications

### `GET /api/applications` → 200

**API-029.**

```json
{
  "items": [
    {
      "id": "b402...",
      "status": "DOCUMENTS_PENDING",
      "property": { "purchase_price": "300000.00", "region": "FLANDERS", "property_type": "EXISTING", "is_first_home": true },
      "documents_required": 7,
      "documents_satisfied": 4,
      "created_at": "...",
      "updated_at": "..."
    }
  ]
}
```

**API-030.** A summary list, not full application bodies. Wrapped in `items` so pagination can be
added later without breaking the shape. `documents_required` and `documents_satisfied` are derived
from the checklist (`DOC-005`), not stored.

**API-031.** No pagination now: a borrower has one or two applications. Stated as a deliberate cut.

### `POST /api/applications` → 201

**API-032.**

```json
{ "simulation_id": "8f1c..." }
```

Creates a draft seeded from the simulation, if one is given and owned by the caller. Returns the full
application body.

**This is the normal path after signup**, not a fallback. It reads the simulation through
`simulation.service` — the cross-domain edge `2-architecture.md` ARC-047 — and it is the reason that
edge exists.

**API-071.** A simulation seeds `region`, `is_first_home` and `purchase_price` — never
`property_type`, because the simulator never asks existing-vs-new-build. The response's `property`
object therefore carries `property_type: null` on a freshly seeded draft, and the wizard's property
step is what fills it in. `2-architecture.md` names the domain type this produces, `PropertySeed`;
added at T21, once this endpoint existed and had to decide what a partially known property section
renders as.

### `GET /api/applications/{id}` → 200

**API-033.**

```json
{
  "id": "b402...",
  "status": "DOCUMENTS_PENDING",
  "simulation_id": "8f1c...",
  "borrowers": [
    {
      "id": "c711...",
      "full_name": "Jan Test",
      "date_of_birth": "1990-04-12",
      "employment_type": "EMPLOYEE",
      "monthly_net_income": "3200.00",
      "has_existing_credit": false
    }
  ],
  "property": {
    "purchase_price": "300000.00",
    "region": "FLANDERS",
    "property_type": "EXISTING",
    "is_first_home": true
  },
  "submitted_at": null,
  "created_at": "...",
  "updated_at": "..."
}
```

**API-034.** 404 `APPLICATION_NOT_FOUND` when it does not exist **or** belongs to another user.

### `PATCH /api/applications/{id}` → 200

**API-035.** Partial update, used by each wizard step. Only the keys present are touched.

```json
{
  "borrowers": [ { "full_name": "Jan Test", "date_of_birth": "1990-04-12", "employment_type": "SELF_EMPLOYED" } ]
}
```

- **API-036** — Only fields present in the body are validated. Steps the borrower has not reached are
  not pre-validated (`UX-032`, `VAL-012`).
- **API-037** — `borrowers` is replaced wholesale when present, not merged element by element.
  Simpler and unambiguous.
- **API-038** — `status` is **not** writable here. Sending it is a 422 (API-011).
- **API-039** — Changing `employment_type` or `property_type` changes the checklist. The response
  includes the updated `status`, and the frontend refetches the checklist.
- **API-040** — 409 `APPLICATION_ALREADY_SUBMITTED` once the application has left the
  document-collection phase — `status` is `UNDER_REVIEW`, `OFFER_ISSUED` or `WITHDRAWN`. **Not**
  once `status` is merely past `DRAFT`: `DOCUMENTS_PENDING` and `DOCUMENTS_COMPLETE` stay writable,
  because `7-validation.md` VAL-020 requires exactly this — "change employment type after uploading
  payslips" only makes sense once documents exist to upload, which is after submission. This
  narrowed at T21; the wording until then said "once submitted" and would have blocked the scenario
  VAL-020 names as expected behaviour. `UNDER_REVIEW` is reached by a manual advance (APP-005), which
  is the point past which the file is being read by a person rather than assembled by the borrower.

  PATCH's own lock (this rule) and submit's re-submission check (API-043) are two different rules
  guarding two different verbs, and each keeps its own code — the PATCH lock stays
  `APPLICATION_ALREADY_SUBMITTED` regardless of state, while submit distinguishes a repeat call from
  a genuinely unreachable one (see API-043 – API-044).

Returns the full application body.

### `POST /api/applications/{id}/submit` → 200

**API-041.** Empty body. Runs full validation across every step, then transitions
`DRAFT → SUBMITTED` (`APP-001`). Returns the full application body.

- **API-042** — 422 `VALIDATION_ERROR` with `field` naming the first missing input.
- **API-043** — 409 `APPLICATION_ALREADY_SUBMITTED` on a second call — any state reached *by*
  submitting once, which in this build means anything but `DRAFT` and `WITHDRAWN`. **Idempotent from
  the client's point of view:** the frontend disables the button while in flight (`UX-035`), and a
  duplicate returns a clear conflict rather than corrupting state.
- **API-044** — 409 `INVALID_STATE_TRANSITION` from `WITHDRAWN` specifically — the one state
  submission was never a path to, so it gets the generic state-machine code rather than the
  submission-specific one. The bare state machine cannot make this distinction on its own (both are
  simply "not `DRAFT`"), so the service checks it before calling `assert_transition` (T21).

## 7. Checklist

### `GET /api/applications/{id}/checklist` → 200

**API-045.**

```json
{
  "required_count": 7,
  "satisfied_count": 4,
  "items": [
    {
      "doc_type": "IDENTITY",
      "label_en": "Identity document",
      "label_nl": "identiteitskaart",
      "required": true,
      "satisfied": true,
      "reason": null,
      "documents": [
        { "id": "d901...", "filename": "id.pdf", "size_bytes": 184320, "uploaded_at": "..." }
      ]
    },
    {
      "doc_type": "PAYSLIPS",
      "label_en": "Recent payslips",
      "label_nl": "loonfiches",
      "required": true,
      "satisfied": false,
      "reason": "Required because you selected employed",
      "documents": []
    }
  ]
}
```

**API-070.** When the optional classifier is enabled
([`9-ai-classification.md`](9-ai-classification.md) AI-025), each object in `documents[]` also carries
`classification_status` and `classification_message` — the latter composed server-side, so the
frontend renders a string and never implements the decision table.

**API-046.** `reason` is populated only for conditional requirements. It is what stops the list
feeling arbitrary and it demonstrates that the checklist is derived rather than fixed — the product
point of the whole build (`UX-038`).

**API-047.** Computed on read. Never stored. → `DOC-005`, `DOM-001`.

## 8. Documents

### `POST /api/applications/{id}/documents` → 201

**API-048.** `multipart/form-data`: `file` plus `doc_type`.

```json
{
  "id": "d901...",
  "doc_type": "PAYSLIPS",
  "filename": "payslip-march.pdf",
  "content_type": "application/pdf",
  "size_bytes": 184320,
  "uploaded_at": "...",
  "application_status": "DOCUMENTS_COMPLETE"
}
```

**API-049.** `application_status` is returned so the frontend can update the header without a second
request. The document row and the status transition happen in **one transaction** — `CQ-091`,
`ARC-018`, `APP-003`.

- **API-050** — 415 `UNSUPPORTED_DOCUMENT_TYPE` — decided by magic bytes, not by extension or the
  client's `Content-Type` (`VAL-022`).
- **API-051** — 413 `DOCUMENT_TOO_LARGE` — enforced by the body-size middleware before the body is
  buffered into memory (`VAL-024`).
- **API-052** — 422 `DOCUMENT_EMPTY`, `DOCUMENT_TYPE_NOT_REQUIRED`.
- **API-053** — 404 `APPLICATION_NOT_FOUND`.

### `GET /api/applications/{id}/documents/{document_id}` → 200

**API-054.** Returns the file bytes with `Content-Disposition: attachment`. Ownership is re-checked on
every request; files are never served as static assets (`VAL-025`, `AUTH-034`).

### `DELETE /api/applications/{id}/documents/{document_id}` → 200

**API-055.**

```json
{ "application_status": "DOCUMENTS_PENDING" }
```

**API-056.** Deleting the last document satisfying a requirement moves the application backwards.
**This is a normal transition, not an error** (`APP-004`, `UX-043`), and the response makes it visible
so the UI can show it.

## 9. Health

**API-057.** `GET /health` → `{"status": "ok"}`. Liveness only, touches nothing (`DEP-036`).

**API-058.** `GET /ready` → `{"status": "ready"}` or 503. Runs `SELECT 1` and checks the blob
directory is writable (`DEP-037`).

## 10. TypeScript models

**API-059.** Mirror the wire format field for field. No camelCase conversion: a renaming layer buys
nothing and will drift (`ARC-027`).

```ts
export type Region = 'FLANDERS' | 'WALLONIA' | 'BRUSSELS';
export type PropertyType = 'EXISTING' | 'NEW_BUILD';
export type EmploymentType = 'EMPLOYEE' | 'SELF_EMPLOYED' | 'OTHER';

export type ApplicationStatus =
  | 'DRAFT' | 'SUBMITTED' | 'DOCUMENTS_PENDING' | 'DOCUMENTS_COMPLETE'
  | 'UNDER_REVIEW' | 'OFFER_ISSUED' | 'WITHDRAWN';

export interface ApiError {
  code: string;
  message: string;
  field?: string;
}

export interface SimulationRequest {
  property_value: string;
  own_contribution: string;
  term_months: number;
  annual_nominal_rate: string;
  region: Region;
  is_first_home: boolean;
}

export interface UpfrontCosts {
  registration_duty: string;
  notary_fee: string;
  mortgage_costs: string;
  dossier_fee: string;
  valuation_fee: string;
  total_costs: string;
  own_contribution: string;
  total_cash_needed: string;
}

export interface Simulation {
  id: string;
  loan_amount: string;
  quotiteit: string;
  above_supervisory_norm: boolean;
  monthly_payment: string;
  total_paid: string;
  total_interest: string;
  nominal_rate: string;
  jkp: string;
  upfront: UpfrontCosts;
  created_at: string;
}

export interface ChecklistItem {
  doc_type: string;
  label_en: string;
  label_nl: string;
  required: boolean;
  satisfied: boolean;
  reason: string | null;
  documents: DocumentSummary[];
}
```

**API-060. Every money and rate field is `string`.** Typing them as `number` re-introduces float
rounding at the one place the whole build is judged on.

## 11. Deliberately absent

**API-061.**

| Absent | Why |
|---|---|
| Pagination | A borrower has one or two applications. The `items` wrapper leaves room to add it. |
| API versioning (`/v1`) | One client, shipped together. Versioning with a single consumer is ceremony. |
| `PUT` | `PATCH` covers partial wizard updates; nothing needs full replacement. |
| Nesting deeper than two levels | `/applications/{id}/documents/{id}` is the limit. Anything deeper becomes unreadable. |
| Bulk endpoints | No use case in these four flows. |
| `PATCH` on documents | Documents are immutable: replace by deleting and re-uploading. |
| Filtering and sorting query params | Nothing to filter at this volume. |
| WebSockets or SSE | Nothing pushes. All state changes originate from the user. |

## 12. Definition of done

- **API-062** — Every endpoint above exists, with these exact paths, bodies and status codes.
- **API-063** — Every error uses the shared shape and a code from the registry, `7-validation.md` §2.
- **API-064** — Money and rates are strings everywhere, in both directions.
- **API-065** — Another user's resource returns 404, never 403.
- **API-066** — `POST /api/simulations` returns the figures in `AC-003` to the cent.
- **API-067** — Uploading a document returns the resulting application status in the same response.
- **API-068** — The TypeScript models compile against the real responses with no `any` and no mapping
  layer.

---

# Appendix A — Traceability

Source: `10-api.md`, superseded by this document.

| ID | Statement | Source § | § |
|---|---|---|---|
| API-001 | All routes prefixed `/api`; health and static are not | Conventions | §1 |
| API-002 | `snake_case` on the wire, no renaming layer | Conventions | §1 |
| API-003 | Path identifiers are UUID4 | Conventions | §1 |
| API-004 | Money is a JSON string, two decimals | Conventions | §1 |
| API-005 | Rates are fraction strings, four decimals | Conventions | §1 |
| API-006 | Ratios are fraction strings, four decimals | Conventions | §1 |
| API-007 | Timestamps are ISO 8601 UTC with `Z` | Conventions | §1 |
| API-008 | Only canonical number formats cross the wire | Conventions | §1 |
| API-009 | No trailing slashes | Conventions | §1 |
| API-010 | The checklist is a sub-resource | Three departures | §1.1 |
| API-011 | State changes are actions, not a PATCH on status | Three departures | §1.1 |
| API-012 | Simulations are POSTed and persisted | Three departures | §1.1 |
| API-013 | The error shape | Error shape | §2 |
| API-014 | `field` only when the error maps to one input | Error shape | §2 |
| API-015 | Pydantic errors normalised; no raw `detail` array | Error shape | §2 |
| API-016 | The seventeen endpoints | Endpoints | §3 |
| API-017 | Session routes scope by `user_id`; 404 not 403 | Endpoints | §3 |
| API-018 | `POST /api/simulations` request and response | Simulations | §4 |
| API-019 | The figures are AC-003, to the cent | Simulations | §4 |
| API-020 | `above_supervisory_norm` is strictly `> 0.90` | Simulations | §4 |
| API-021 | `GET /api/simulations/{id}` is public | Simulations | §4 |
| API-022 | 404 `SIMULATION_NOT_FOUND` | Simulations | §4 |
| API-023 | Signup request and response | Auth | §5 |
| API-024 | A failed claim never fails signup; no `application_id` | Auth, corrected at T17 | §5 |
| API-071 | A seeded draft has `property_type: null` until the wizard fills it | added at T21 | §6 |
| API-025 | 409 `EMAIL_ALREADY_REGISTERED` | Auth | §5 |
| API-026 | Login contract and the identical 401 | Auth | §5 |
| API-027 | Logout returns 204 either way | Auth | §5 |
| API-028 | `GET /api/auth/me` or 401 | Auth | §5 |
| API-029 | The application summary list | Applications | §6 |
| API-030 | Wrapped in `items`; counts are derived | Applications | §6 |
| API-031 | No pagination, deliberately | Applications | §6 |
| API-032 | `POST /api/applications` seeds a draft | Applications | §6 |
| API-033 | The full application body | Applications | §6 |
| API-034 | 404 for absent or someone else's | Applications | §6 |
| API-035 | `PATCH` is a partial update per wizard step | Applications | §6 |
| API-036 | Only present fields are validated | Applications | §6 |
| API-037 | `borrowers` is replaced wholesale | Applications | §6 |
| API-038 | `status` is not writable via PATCH | Applications | §6 |
| API-039 | Changing employment or property type changes the checklist | Applications | §6 |
| API-040 | 409 once past document collection, not once past DRAFT | Applications, corrected at T21 | §6 |
| API-041 | `submit` runs full validation and transitions | Applications | §6 |
| API-042 | 422 with `field` naming the first missing input | Applications | §6 |
| API-043 | 409 on a second submit; client-side idempotent | Applications | §6 |
| API-044 | 409 `INVALID_STATE_TRANSITION` from any other state | Applications | §6 |
| API-045 | The checklist response | Checklist | §7 |
| API-046 | `reason` only for conditional requirements | Checklist | §7 |
| API-047 | Computed on read, never stored | Checklist | §7 |
| API-048 | Document upload is multipart; the response body | Documents | §8 |
| API-049 | `application_status` returned; one transaction | Documents | §8 |
| API-050 | 415 decided by magic bytes | Documents | §8 |
| API-051 | 413 enforced by the body-size middleware | Documents | §8 |
| API-052 | 422 `DOCUMENT_EMPTY`, `DOCUMENT_TYPE_NOT_REQUIRED` | Documents | §8 |
| API-053 | 404 `APPLICATION_NOT_FOUND` | Documents | §8 |
| API-054 | Download re-checks ownership; never static | Documents | §8 |
| API-055 | Delete returns the resulting status | Documents | §8 |
| API-056 | Moving backwards is a normal transition | Documents | §8 |
| API-057 | `/health` body | Health | §9 |
| API-058 | `/ready` body or 503 | Health | §9 |
| API-059 | TypeScript models mirror the wire | TypeScript models | §10 |
| API-060 | Every money and rate field is `string` | TypeScript models | §10 |
| API-061 | Eight things deliberately absent | Deliberately absent | §11 |
| API-062 | Done: every endpoint with these exact contracts | Definition of done | §12 |
| API-063 | Done: shared error shape, registered codes | Definition of done | §12 |
| API-064 | Done: money and rates are strings both ways | Definition of done | §12 |
| API-065 | Done: 404, never 403 | Definition of done | §12 |
| API-066 | Done: the simulation figures match AC-003 | Definition of done | §12 |
| API-067 | Done: upload returns the resulting status | Definition of done | §12 |
| API-068 | Done: the TS models compile with no `any` | Definition of done | §12 |
| API-069 | `/health` and `/ready` sit outside the error contract | added in review | §2 |
| API-070 | Checklist documents carry the classification fields | added for `9-ai-classification.md` | §7 |

# Appendix B — Corrections against the specs

| Item | Resolution |
|---|---|
| `SIM-020` had `200 OK`, `"annual_nominal_rate": "0.04"` and no `created_at` | This spec is canonical for the wire. 201 is correct for a created resource, `VAL-019` already required four decimals on rates, and `created_at` is returned. `SIM-020` now points here; the figures stay in `AC-003`. |
| `updated_at` (Application) and `id` (Borrower) | Neither appeared in `DOM-021` / `DOM-022`. Both are stored columns and were added to the business spec. |
| `DOC-009` fixed the checklist response at five fields | The richer shape — `reason`, `documents[]`, `required_count`, `satisfied_count` — is canonical here; `DOC-009` points at §7. |
| `AUTH-039` omitted `logout` from the public routes | Corrected there; `AUTH-028` already made it work without a session. |
