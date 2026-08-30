"""Pydantic request and response models for the document wire contract."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import DocumentType
from app.domains.simulation.schemas import Money


class ProposalResponse(BaseModel):
    """What one document suggests for the financial profile (T58).

    **A suggestion, never a value.** It pre-fills the finances form; only what
    the borrower then confirms is stored and calculated on (DOM-030). Present
    only when classification agreed the document is what was claimed — figures
    read off a document that turned out to be something else describe the wrong
    document.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    net_monthly_income: Money | None
    existing_credit_monthly: Money | None
    source: str


class DocumentSummary(BaseModel):
    """One uploaded file, as nested under a checklist row (API-045).

    No `doc_type`: it is redundant with the row it sits under, and no
    `storage_key`: that is an internal detail, never rendered (DOC-003).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    filename: str
    size_bytes: int
    uploaded_at: datetime
    # AI-025. Both null with the classifier off, and both null for any outcome
    # not worth a sentence — the row then renders exactly as it always has.
    classification_status: str | None = None
    classification_message: str | None = None
    proposal: ProposalResponse | None = None


class ChecklistItem(BaseModel):
    """One row of the derived checklist (API-045, API-046)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    doc_type: DocumentType
    label_en: str
    label_nl: str
    required: bool
    satisfied: bool
    reason: str | None
    documents: list[DocumentSummary]


class ChecklistResponse(BaseModel):
    """The full checklist: counts, then rows (API-045, API-047)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    required_count: int
    satisfied_count: int
    items: list[ChecklistItem]


class DocumentResponse(BaseModel):
    """The result of an upload (API-048).

    `application_status` rides along so the frontend can update the header
    without a second request — the row and the status move in one transaction
    (API-049, CQ-091).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    doc_type: DocumentType
    filename: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
    application_status: str


class DocumentDeleteResponse(BaseModel):
    """The result of a delete (API-055)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    application_status: str
