"""Queries against the documents table."""

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DocumentType
from app.domains.documents.entities import Document
from app.domains.documents.tables import DocumentRow


class DocumentRepository(Protocol):
    """Persistence for uploaded documents."""

    async def create(self, session: AsyncSession, document: Document) -> Document:
        """Insert a document row."""
        ...

    async def get(self, session: AsyncSession, document_id: UUID) -> Document | None:
        """Fetch one document, or None."""
        ...

    async def list_for_application(
        self, session: AsyncSession, application_id: UUID
    ) -> list[Document]:
        """Every document attached to an application."""
        ...

    async def delete(self, session: AsyncSession, document_id: UUID) -> None:
        """Remove a document row."""
        ...

    async def uploaded_types_for(
        self, session: AsyncSession, application_ids: Sequence[UUID]
    ) -> dict[UUID, frozenset[DocumentType]]:
        """The distinct document types held by each of these applications."""
        ...

    async def set_classification(
        self, session: AsyncSession, result: "ClassificationRecord"
    ) -> None:
        """Record whether classification ran and what it decided (AI-020)."""
        ...

    async def classifications_for(
        self, session: AsyncSession, application_id: UUID
    ) -> dict[UUID, "ClassificationRecord"]:
        """Advisory classification columns, keyed by document id."""
        ...


@dataclass(frozen=True, slots=True)
class ClassificationRecord:
    """One document's classification result, bundled to stay inside CQ-038.

    Advisory columns only (AI-020): `outcome` is null unless `status` is DONE,
    and neither ever touches `doc_type` (AI-017).
    """

    document_id: UUID
    status: str
    outcome: str | None
    detected_type: str | None = None
    # T57/T58. What the document proposed for the financial profile — a
    # suggestion the borrower confirms, never a value anything calculates on
    # (DOM-030).
    proposed_income: Decimal | None = None
    proposed_credit: Decimal | None = None
    proposal_source: str | None = None


def _to_entity(row: DocumentRow) -> Document:
    """Map a row to the domain type."""
    return Document(
        id=row.id,
        application_id=row.application_id,
        doc_type=DocumentType(row.doc_type),
        filename=row.filename,
        storage_key=row.storage_key,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        uploaded_at=row.uploaded_at,
    )


class SqlDocumentRepository:
    """The SQLite implementation of `DocumentRepository`."""

    async def create(self, session: AsyncSession, document: Document) -> Document:
        """Insert a document row and return it as an entity."""
        row = DocumentRow(
            id=document.id,
            application_id=document.application_id,
            doc_type=document.doc_type.value,
            filename=document.filename,
            storage_key=document.storage_key,
            content_type=document.content_type,
            size_bytes=document.size_bytes,
            uploaded_at=document.uploaded_at,
        )
        session.add(row)
        await session.flush()
        return _to_entity(row)

    async def get(self, session: AsyncSession, document_id: UUID) -> Document | None:
        """Fetch one document, or None."""
        row = await session.get(DocumentRow, document_id)
        return _to_entity(row) if row else None

    async def uploaded_types_for(
        self, session: AsyncSession, application_ids: Sequence[UUID]
    ) -> dict[UUID, frozenset[DocumentType]]:
        """The distinct document types held by each of these applications.

        Two columns, not entities: the summary list needs to know *which types*
        an application has, and loading every row to count them would read the
        filename and size of every file the borrower ever uploaded to answer a
        question about set membership.
        """
        if not application_ids:
            return {}
        statement = select(DocumentRow.application_id, DocumentRow.doc_type).where(
            DocumentRow.application_id.in_(application_ids)
        )
        uploaded: dict[UUID, set[DocumentType]] = {}
        for application_id, doc_type in (await session.execute(statement)).all():
            uploaded.setdefault(application_id, set()).add(DocumentType(doc_type))
        return {key: frozenset(value) for key, value in uploaded.items()}

    async def list_for_application(
        self, session: AsyncSession, application_id: UUID
    ) -> list[Document]:
        """Every document attached to an application, oldest first."""
        statement = (
            select(DocumentRow)
            .where(DocumentRow.application_id == application_id)
            .order_by(DocumentRow.uploaded_at)
        )
        rows = (await session.execute(statement)).scalars().all()
        return [_to_entity(row) for row in rows]

    async def delete(self, session: AsyncSession, document_id: UUID) -> None:
        """Remove a document row. The blob is removed by the service."""
        await session.execute(delete(DocumentRow).where(DocumentRow.id == document_id))
        await session.flush()

    async def set_classification(
        self, session: AsyncSession, result: ClassificationRecord
    ) -> None:
        """Annotate one row. Advisory only: never touches `doc_type` (AI-017).

        A document deleted between the upload and this task finishing is a
        normal race rather than an error — there is simply nothing left to
        annotate, and the task has nobody to report it to anyway.
        """
        row = await session.get(DocumentRow, result.document_id)
        if row is None:
            return
        row.classification_status = result.status
        row.classification_outcome = result.outcome
        row.classification_detected_type = result.detected_type
        row.proposed_income = result.proposed_income
        row.proposed_credit = result.proposed_credit
        row.proposal_source = result.proposal_source
        await session.flush()

    async def classifications_for(
        self, session: AsyncSession, application_id: UUID
    ) -> dict[UUID, ClassificationRecord]:
        """Advisory columns for one application's documents, keyed by document id.

        A separate read rather than fields on the `Document` entity: AI-020
        keeps the domain type free of this feature, so it stays readable — and
        the flag stays genuinely removable — without knowing the classifier
        exists.
        """
        statement = select(DocumentRow).where(DocumentRow.application_id == application_id)
        rows = (await session.execute(statement)).scalars().all()
        return {
            row.id: ClassificationRecord(
                document_id=row.id,
                status=row.classification_status or "",
                outcome=row.classification_outcome,
                detected_type=row.classification_detected_type,
                proposed_income=row.proposed_income,
                proposed_credit=row.proposed_credit,
                proposal_source=row.proposal_source,
            )
            for row in rows
        }
