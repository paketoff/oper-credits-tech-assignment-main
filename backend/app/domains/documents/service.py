"""Document flow: validate, store the blob, write the row, move the application."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.applications.entities import DocumentRequirement
from app.domains.applications.service import ApplicationService
from app.domains.documents.entities import Document
from app.domains.documents.repository import DocumentRepository
from app.domains.documents.schemas import ChecklistItem, ChecklistResponse, DocumentSummary


class DocumentService:
    """Uploaded documents and the derived checklist that reads them.

    Depends on `ApplicationService` — the cross-domain edge `ARC-018`, widened
    past `recompute_status` at T22 to cover `checklist()` and `get_owned()` too.
    Neither service reaches into the other's repository (ARC-011, ARC-019).
    """

    def __init__(self, repository: DocumentRepository, applications: ApplicationService) -> None:
        """Take the repository as a protocol, and the one foreign service."""
        self._repository = repository
        self._applications = applications

    async def checklist(
        self, session: AsyncSession, application_id: UUID, user_id: UUID
    ) -> ChecklistResponse:
        """Derive and render the checklist for one application (API-045).

        Raises:
            NotFoundError: APPLICATION_NOT_FOUND for someone else's
                application, via `applications.get_owned` (AUTH-035).
        """
        application = await self._applications.get_owned(session, application_id, user_id)
        documents = await self._repository.list_for_application(session, application_id)
        uploaded_types = frozenset(document.doc_type for document in documents)

        requirements = self._applications.checklist(application, uploaded_types)
        items = [self._to_item(requirement, documents) for requirement in requirements]
        required = [item for item in items if item.required]
        return ChecklistResponse(
            required_count=len(required),
            satisfied_count=sum(1 for item in required if item.satisfied),
            items=items,
        )

    def _to_item(
        self, requirement: DocumentRequirement, documents: list[Document]
    ) -> ChecklistItem:
        """Assemble one row, nesting the documents that satisfy it.

        A requirement is satisfied by *any* document of its type (DOC-008), so
        every matching upload is nested here — not only the first.
        """
        matching = [d for d in documents if d.doc_type == requirement.doc_type]
        return ChecklistItem(
            doc_type=requirement.doc_type,
            label_en=requirement.label_en,
            label_nl=requirement.label_nl,
            required=requirement.required,
            satisfied=requirement.satisfied,
            reason=requirement.reason,
            documents=[
                DocumentSummary(
                    id=d.id, filename=d.filename, size_bytes=d.size_bytes, uploaded_at=d.uploaded_at
                )
                for d in matching
            ],
        )
