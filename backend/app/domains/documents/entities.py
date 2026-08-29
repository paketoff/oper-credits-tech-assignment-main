"""Domain types for stored documents."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.core.enums import DocumentType


@dataclass(frozen=True, slots=True)
class Document:
    """One uploaded file.

    `storage_key` is opaque and generated; `filename` is the borrower's original
    name, sanitised, and is metadata only. The backend never serves by a
    user-supplied path (DOC-003, DOC-004, VAL-023).

    `doc_type` is what the borrower declared on upload, and nothing overrides it
    — including the optional classifier, which warns and never reassigns
    (DOC-010, AI-017).
    """

    id: UUID
    application_id: UUID
    doc_type: DocumentType
    filename: str
    storage_key: str
    content_type: str
    size_bytes: int
    uploaded_at: datetime
