"""Queries against the documents table."""

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
        )
        session.add(row)
        await session.flush()
        return _to_entity(row)

    async def get(self, session: AsyncSession, document_id: UUID) -> Document | None:
        """Fetch one document, or None."""
        row = await session.get(DocumentRow, document_id)
        return _to_entity(row) if row else None

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
