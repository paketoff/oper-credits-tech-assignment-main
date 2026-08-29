"""SQLAlchemy definition of the documents table."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


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
