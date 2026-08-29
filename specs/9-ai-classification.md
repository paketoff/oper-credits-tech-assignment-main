---
id: AI
title: AI Document Classification
status: draft
version: 1.0.0
owner: paketoff
updated: 2026-08-29
---

# 9 — AI Document Classification

Companion to [`0-business-logic.md`](0-business-logic.md) (the checklist) and
[`8-api.md`](8-api.md) (the upload contract).

**AI-001. This is the last feature built.** It is only started once every core flow works end to end
on the deployed URL. If time runs out, this document ships as a described next step and nothing is
lost.

## 1. What it does

**AI-002.** When a borrower uploads a file against a checklist requirement, a model looks at the first
page and says what the document actually is. The result is compared against what the borrower claimed
to be uploading.

Upload a bank statement under "payslips" and you get a warning before the file goes into the file,
rather than a rejection letter three weeks later.

## 2. Why this one

Oper's own homepage states that around 80% of mortgage files arrive incomplete, that dozens of
documents are verified by hand, and that credit policies are applied from memory. Their flagship
product is an agentic AI credit analyst that classifies documents, extracts data and applies a
written policy.

A borrower portal that catches the wrong document at the moment of upload attacks the same problem
from the other end of the funnel, and it costs one API call.

## 3. The architectural decision

**AI-003. The model produces a structured verdict. Deterministic code owns the outcome.**

The model returns a document type and a confidence. It does not decide whether the file is accepted,
whether the requirement is satisfied, or whether the application status changes. Code compares the
verdict to the expected type, applies thresholds, and decides what the borrower sees.

Three reasons this matters, in this order:

**Correctness.** A model that classifies a payslip as a tax assessment cannot corrupt the application
state, because it has no authority over state. The worst case is an unhelpful hint.

**The domain.** Mortgage lending is regulated. Oper is explicit that their agent applies a *written*
credit policy and is "not credit scoring", with a human in the loop and an audit trail, aligned with
the EU AI Act. An AI feature that silently made decisions would read as naive to anyone from this
industry.

**It is defensible.** The interesting question on a walkthrough is not "did you call an LLM" but
"what happens when it is wrong". This design has an answer.

## 4. Boundaries

Three rules. Breaking any of them turns the feature into a liability.

**AI-004. 1. Behind a feature flag.** `AI_CLASSIFICATION_ENABLED`, read from the environment, default
off. With it off, the application behaves exactly as it did before. The API key is revoked after the
interview call — the deployed app must not degrade when that happens. → `5-deployment.md` DEP-018,
DEP-024.

**AI-005. 2. Never blocks the upload.** The file is stored, the document row is written, the
application status is recalculated, and the response returns. Classification happens afterwards. If it
fails, times out, or the API is unreachable, the document is still accepted and the borrower is
unaffected.

**AI-006. 3. A hint, never a decision.** A mismatch shows a warning with a "keep it anyway" action.
The borrower is right and the model is guessing. Rejecting a document on a model's guess is a worse
failure than accepting a wrong one.

## 5. Contract with the model

### 5.1 Input

- **AI-007** — The **first page only**, rendered to a PNG at 150 DPI, max 1500px on the long edge. One
  page is enough to identify a document type and keeps the call cheap and fast.
- **AI-008** — PDFs are rendered with `pdf2image`; JPEG and PNG uploads are downscaled and sent
  directly.

### 5.2 Not sent, deliberately

**AI-009.**

- Nothing after page one.
- The original filename. It is borrower-controlled, often reveals a real name, and would let the
  model classify from the name rather than the content — which is exactly the shortcut that makes the
  feature useless.
- Any application, borrower or account data. The call sees an image and nothing else.

### 5.3 Prompt

**AI-010.** System prompt, kept in `domains/documents/classification/prompts.py` as a module-level
constant so it is versionable and reviewable in a diff:

```
You classify supporting documents for a Belgian mortgage application.

Look only at the image. Decide which single category it belongs to:

IDENTITY              - identity card or passport
PAYSLIPS              - loonfiche / fiche de paie, a monthly salary slip
EMPLOYER_STATEMENT    - werkgeversattest or employment contract
TAX_ASSESSMENT        - aanslagbiljet / avertissement-extrait de rôle
BANK_STATEMENTS       - rekeninguittreksel, an account statement
PURCHASE_AGREEMENT    - compromis / verkoopovereenkomst, a sale agreement
EPC                   - energieprestatiecertificaat, an energy performance certificate
BUILDING_PERMIT       - bouwvergunning, a planning permit
CONSTRUCTION_QUOTE    - bestek or prijsofferte, a construction quote
EXISTING_LOAN_STATEMENTS - a statement for an existing credit
ACCOUNTANT_STATEMENT  - a statement of income prepared by an accountant
UNKNOWN               - anything else, or too unclear to tell

Documents may be in Dutch, French, English or German.

Respond with JSON only, no prose:
{"doc_type": "<one category>", "confidence": <0.0-1.0>, "reason": "<max 15 words>"}

Set UNKNOWN with low confidence when unsure. A wrong confident answer is worse
than an honest UNKNOWN.
```

### 5.4 Output

**AI-011.** Parsed into a frozen pydantic model (`1-code-quality.md` CQ-025, CQ-026). Anything that
fails to parse, or names a category outside the enum, is treated as `UNKNOWN` at confidence 0.

```python
class ClassificationVerdict(BaseModel):
    """What the model thinks a document is. Advisory only."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    doc_type: ClassifiedType
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=120)
```

**AI-012.** `ClassifiedType` is the domain `DocumentType` plus `UNKNOWN`, and it lives in the
classification module. **The domain `DocumentType` is not extended.** `UNKNOWN` is a classifier
output, never a checklist requirement and never the `doc_type` of a stored document — the eleven
types of `DOC-006` and `DOC-007` stay exactly as they are.

**AI-013.** Model: `claude-sonnet-5`. `max_tokens` 300 — the response is four fields, and a low cap
bounds both cost and latency.

## 6. The deterministic layer

**AI-014.** A pure function. No IO, no API client, no session. This is where the outcome is decided
and it is fully unit-testable without touching the network. → `2-architecture.md` ARC-008, ARC-013.

```python
def evaluate(verdict: ClassificationVerdict, claimed: DocumentType) -> ClassificationOutcome:
    """Decide what to tell the borrower about a classified document.

    The model's verdict is advisory. This function owns the outcome, so a wrong
    or low-confidence verdict can never change application state.
    """
```

**AI-015.**

| Condition | Outcome | Shown to the borrower |
|---|---|---|
| `confidence < 0.60` | `INCONCLUSIVE` | Nothing. Silence beats a bad guess. |
| `doc_type == claimed` and `confidence >= 0.60` | `CONFIRMED` | A quiet checkmark on the row. |
| `doc_type == UNKNOWN` and `confidence >= 0.60` | `UNRECOGNISED` | "We could not recognise this document. Check it is the right file and readable." |
| `doc_type != claimed` and `0.60 <= confidence < 0.85` | `POSSIBLE_MISMATCH` | "This may be a {actual} rather than a {claimed}." |
| `doc_type != claimed` and `confidence >= 0.85` | `LIKELY_MISMATCH` | "This looks like a {actual}, but it was uploaded as {claimed}." Plus "Keep it anyway" and "Replace". |

**AI-016. Both thresholds are named constants, not literals.** They are the tuning surface of the
whole feature and they are the first thing to ask about on a walkthrough.

**AI-017.** No outcome changes `Document.doc_type`, satisfies or unsatisfies a requirement, or moves
the application. The requirement is satisfied by what the borrower declared, exactly as before this
feature existed — `DOC-005` – `DOC-008`, and it is what keeps `SCP-015` true in substance.

## 7. Pipeline

**AI-018.** Upload is synchronous. Classification is not.

```
POST /documents
  → validate magic bytes, store blob, insert row, recalc status   [transaction commits]
  → return 201                                                     [borrower is done]
  → background task: render page 1 → call model → evaluate → persist outcome
```

The transaction boundary is the service's (`CQ-091`); the background task starts after it commits.

**AI-019.** FastAPI `BackgroundTasks` is enough. Celery would be correct at scale and is noted as a
next step; adding a broker here would be infrastructure for its own sake.

### 7.1 Classification states

**AI-020.** Stored on the document row: `classification_status` and `classification_outcome`. These
two columns exist only for this feature; the core `Document` entity in `0-business-logic.md` §9.5 is
unchanged and readable with the flag off.

```
PENDING     queued, not yet run
CONFIRMED | POSSIBLE_MISMATCH | LIKELY_MISMATCH | UNRECOGNISED | INCONCLUSIVE
FAILED      the call errored or timed out
SKIPPED     the feature flag is off
```

**AI-021.** `FAILED` and `SKIPPED` render identically to the borrower: as nothing. A failed
classification is invisible, because it is our problem and not theirs.

### 7.2 Failure handling

- **AI-022** — 10-second timeout on the API call. One retry on a network error, none on a 4xx.
- **AI-023** — Any exception sets `FAILED`, logs the error with the document id, and stops. It never
  propagates toward the borrower.
- **AI-024** — With the flag off, no client is constructed and no key is read.

## 8. API additions

**AI-025.** [`8-api.md`](8-api.md) extends. No new endpoint.

The document object in the checklist response gains:

```json
{
  "id": "d901...",
  "filename": "march.pdf",
  "size_bytes": 184320,
  "uploaded_at": "...",
  "classification_status": "LIKELY_MISMATCH",
  "classification_message": "This looks like a bank statement, but it was uploaded as payslips."
}
```

**AI-026.** `classification_message` is composed server-side from the outcome and the two type labels.
The frontend renders a string; it does not implement the decision table.

**AI-027.** `PENDING` renders as a subtle spinner on the row. Everything else is a static state. The
frontend polls the checklist once, three seconds after an upload, and stops — no websocket, no polling
loop.

## 9. Privacy

The same rule as the rest of the telemetry layer in [`5-deployment.md`](5-deployment.md) DEP-035, and
it matters more here because the payload is a photograph of someone's identity card.

- **AI-028. Never logged, never a span attribute, never a metric label:** the image, any text
  extracted from it, the original filename, the model's `reason` field.
- **AI-029. Logged:** document id, claimed type, returned type, confidence bucket (`low`, `medium`,
  `high`), outcome, latency.
- **AI-030.** One span, `document.classify`, with those attributes and no others. This is the third
  manual span, alongside the two in DEP-032.
- **AI-031.** The image is held in memory for the duration of the call and never written to disk as a
  separate artefact.

## 10. Tests

**AI-032.** Four. The first three need no network.

1. **AI-033** — `evaluate` returns `INCONCLUSIVE` below the confidence floor, even when the types
   disagree sharply. This is the test that proves the code, not the model, owns the outcome.
2. **AI-034** — `evaluate` covers every row of the decision table, parameterised.
3. **AI-035** — A malformed model response degrades to `UNKNOWN` at confidence 0 — invalid JSON, an
   unknown category, a confidence of 2.0, an empty body.
4. **AI-036** — Upload succeeds when the classifier raises. Mock the client to throw; assert 201, the
   document row exists, the application status is correct, and `classification_status` is `FAILED`.

**AI-037.** Test 4 is the one worth pointing at: it proves AI-005 holds.

## 11. Not built

**AI-038.**

| Not built | Why |
|---|---|
| Field extraction (income, dates, account numbers) | The natural next step and where the real value is. Needs per-type schemas and a verification story. Remains cut as `SCP-015`. |
| Cross-checking data between documents | Payslip against tax assessment against bank statement. This is what an underwriter actually does and it is a product, not a feature. |
| Multi-page documents | Page one identifies the type. More pages are needed for extraction, not classification. |
| OCR of handwriting and poor scans | The model handles legible scans. Anything worse is a real problem and a real research task. |
| Automatic reclassification | Never move a document to a type the borrower did not choose. The borrower decides; the model advises. |
| Duplicate detection | Cheap by hash, but out of scope here. |

## 12. Definition of done

- **AI-039** — With `AI_CLASSIFICATION_ENABLED=false`, the application behaves exactly as it did
  before this feature.
- **AI-040** — Uploading with a broken or absent API key returns 201 and stores the document.
- **AI-041** — A confident mismatch shows a warning with a "keep it anyway" action, and the
  requirement stays satisfied.
- **AI-042** — No classification outcome changes `doc_type`, checklist satisfaction, or application
  status.
- **AI-043** — No image, filename or extracted text appears in any log line or span attribute.
- **AI-044** — Both confidence thresholds are named constants in one module.

---

# Appendix A — Traceability

Source: `11-ai-classification.md`, superseded by this document.

| ID | Statement | Source § | § |
|---|---|---|---|
| AI-001 | This is the last feature built | preamble | intro |
| AI-002 | Page one is classified and compared to the claim | What it does | §1 |
| AI-003 | The model advises; deterministic code owns the outcome | The architectural decision | §3 |
| AI-004 | Behind `AI_CLASSIFICATION_ENABLED`, default off | Boundaries, 1 | §4 |
| AI-005 | Never blocks the upload | Boundaries, 2 | §4 |
| AI-006 | A hint, never a decision | Boundaries, 3 | §4 |
| AI-007 | First page only, PNG at 150 DPI, max 1500px | Contract — Input | §5.1 |
| AI-008 | PDFs via `pdf2image`; images downscaled | Contract — Input | §5.1 |
| AI-009 | Filename and all account data deliberately not sent | Contract — Not sent | §5.2 |
| AI-010 | The system prompt, as a module-level constant | Contract — Prompt | §5.3 |
| AI-011 | Frozen verdict model; unparseable degrades to UNKNOWN | Contract — Output | §5.4 |
| AI-012 | `ClassifiedType` is separate; `DocumentType` is not extended | added — keeps UNKNOWN out of the checklist | §5.4 |
| AI-013 | Model and `max_tokens` | Contract — Output | §5.4 |
| AI-014 | `evaluate` is pure | The deterministic layer | §6 |
| AI-015 | The five-row decision table | The deterministic layer | §6 |
| AI-016 | Both thresholds are named constants | The deterministic layer | §6 |
| AI-017 | No outcome changes doc_type, satisfaction or status | The deterministic layer | §6 |
| AI-018 | The pipeline; classification runs after the commit | Pipeline | §7 |
| AI-019 | `BackgroundTasks` is enough; Celery is a next step | Pipeline | §7 |
| AI-020 | The seven classification states, on two columns | Classification states | §7.1 |
| AI-021 | `FAILED` and `SKIPPED` render as nothing | Classification states | §7.1 |
| AI-022 | 10-second timeout, one retry on a network error | Failure handling | §7.2 |
| AI-023 | Any exception sets `FAILED` and stops | Failure handling | §7.2 |
| AI-024 | With the flag off, no client and no key | Failure handling | §7.2 |
| AI-025 | The API extends; no new endpoint | API additions | §8 |
| AI-026 | `classification_message` is composed server-side | API additions | §8 |
| AI-027 | `PENDING` spins; one poll after three seconds | API additions | §8 |
| AI-028 | Never logged: image, text, filename, `reason` | Privacy | §9 |
| AI-029 | Logged: ids, types, confidence bucket, outcome, latency | Privacy | §9 |
| AI-030 | One span, `document.classify` | Privacy | §9 |
| AI-031 | The image is never written to disk | Privacy | §9 |
| AI-032 | Four tests; the first three need no network | Tests | §10 |
| AI-033 | `INCONCLUSIVE` below the floor even on sharp disagreement | Tests | §10 |
| AI-034 | Every row of the decision table, parameterised | Tests | §10 |
| AI-035 | A malformed response degrades to UNKNOWN at 0 | Tests | §10 |
| AI-036 | Upload succeeds when the classifier raises | Tests | §10 |
| AI-037 | Test 4 proves AI-005 | Tests | §10 |
| AI-038 | Six things not built | Not built | §11 |
| AI-039 | Done: flag off behaves exactly as before | Definition of done | §12 |
| AI-040 | Done: a broken key still returns 201 | Definition of done | §12 |
| AI-041 | Done: a confident mismatch warns, stays satisfied | Definition of done | §12 |
| AI-042 | Done: no outcome changes domain state | Definition of done | §12 |
| AI-043 | Done: no image, filename or text in telemetry | Definition of done | §12 |
| AI-044 | Done: both thresholds are named constants | Definition of done | §12 |

# Appendix B — Corrections against the source

| Item | Resolution |
|---|---|
| The source specifies `claude-sonnet-4-6` | **`claude-sonnet-5`.** The named model is real but superseded: Sonnet 5 is the same tier and the same 1M context at $2/$10 per Mtok instead of $3/$15. For a four-field classification response there is no reason to pay more for an older model. |
| `ClassificationVerdict.doc_type: DocumentType` with `UNKNOWN` among the categories | `UNKNOWN` would enter the domain enum that `DOC-006` and `DOC-007` build the checklist from. Split into `ClassifiedType` (AI-012); the domain enum is untouched. |
| `SCP-015` cut "real document classification / extraction" | Narrowed rather than withdrawn. Classification is built here, advisory only; extraction and cross-document checking remain cut. A requirement is still satisfied by the declared type, which is what the cut actually protected. |
| `DEP-024` flagged `ANTHROPIC_API_KEY` as having no declared consumer | Closed. This spec is the consumer. |
| `01-domain.md`, `10-api.md`, `07-deployment.md` references | Rewritten to `0-business-logic.md`, `8-api.md`, `5-deployment.md` |
