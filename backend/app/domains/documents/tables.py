"""SQLAlchemy definition of the documents table."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

_MONEY = Numeric(12, 2)


class DocumentRow(Base):
    """One uploaded file.

    The bytes are not here. They live on the filesystem under `storage_key`,
    which is opaque and generated (ARC-010, DOC-003) — a blob in the database
    would put a 10 MB scan of an identity card into every backup of every row.

    The composite index on `(application_id, doc_type)` is the query the
    checklist runs on every read: which types does this application already
    have (DOC-008, CQ-085).
    """

    __tablename__ = "documents"
    __table_args__ = (Index("ix_documents_application_doc_type", "application_id", "doc_type"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    doc_type: Mapped[str] = mapped_column(String(32))
    filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(128))
    content_type: Mapped[str] = mapped_column(String(64))
    size_bytes: Mapped[int]
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    # AI-020. These two exist only for the optional classifier, and the domain
    # `Document` entity deliberately does not carry them: with the feature off
    # they stay null and nothing reads them, so the domain stays readable
    # without knowing the feature exists.
    #
    # Two columns rather than one because they answer different questions.
    # `classification_status` is the lifecycle — did it run at all. `outcome`
    # is the evaluator's verdict, and is null unless the status is DONE.
    classification_status: Mapped[str | None] = mapped_column(String(24), nullable=True)
    classification_outcome: Mapped[str | None] = mapped_column(String(24), nullable=True)
    # AI-025's sentence names the type the model actually saw ("this looks like
    # a bank statement"), which the outcome alone cannot supply. A third column
    # rather than parsing it back out of a composed string.
    classification_detected_type: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # T57/T58. What this document proposed for the financial profile. Advisory
    # like the columns above: a proposal the borrower confirms into
    # `application_financials`, never something the assessment reads directly
    # (DOM-030).
    proposed_income: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    proposed_credit: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    proposal_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
