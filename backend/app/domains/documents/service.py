"""Document flow: validate, store the blob, write the row, move the application."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DocumentType
from app.core.errors import ApplicationError, DocumentError, NotFoundError
from app.core.storage import StorageBackend
from app.domains.applications.entities import Application, ApplicationStatus, DocumentRequirement
from app.domains.applications.schemas import ApplicationListResponse
from app.domains.applications.service import ApplicationService
from app.domains.documents.classification import messages
from app.domains.documents.classification.entities import claimed_as_classified
from app.domains.documents.classification.pipeline import ClassificationPipeline
from app.domains.documents.entities import Document
from app.domains.documents.file_type import detect_content_type
from app.domains.documents.repository import ClassificationRecord, DocumentRepository
from app.domains.documents.schemas import (
    ChecklistItem,
    ChecklistResponse,
    DocumentDeleteResponse,
    DocumentResponse,
    DocumentSummary,
    ProposalResponse,
)

# DOC-002, VAL-013.
_MIN_SIZE_BYTES = 1

# VAL-013: "Application state must not be SUBMITTED before documents open, nor
# WITHDRAWN." Documents open at DOCUMENTS_PENDING. No registry code names this
# exactly, so it reuses INVALID_STATE_TRANSITION (409) — a conflict with the
# resource's current state, the same class of failure the code already covers
# (VAL-005) — rather than inventing a code CQ-063 would then have to register.
_UPLOAD_OPEN_STATES = frozenset(
    {ApplicationStatus.DOCUMENTS_PENDING, ApplicationStatus.DOCUMENTS_COMPLETE}
)


@dataclass(frozen=True, slots=True)
class UploadRequest:
    """One file, on its way in.

    Bundled so `upload()` stays under CQ-038's four-parameter limit without
    folding an unrelated concept into one.
    """

    doc_type: DocumentType
    filename: str
    content: bytes


@dataclass(frozen=True, slots=True)
class UploadContext:
    """Who is uploading, to which application, and where to schedule follow-up.

    Bundled to stay inside CQ-038's four slots: `upload` already takes the
    session and the request body, and classification needs FastAPI's
    `BackgroundTasks` to reach the service without the router acquiring a
    second service call (CQ-018).
    """

    application_id: UUID
    user_id: UUID
    background_tasks: BackgroundTasks


class DocumentService:
    """Uploaded documents and the derived checklist that reads them.

    Depends on `ApplicationService` — the cross-domain edge `ARC-018`, widened
    past `recompute_status` at T22 to cover `checklist()` and `get_owned()` too.
    Neither service reaches into the other's repository (ARC-011, ARC-019).
    """

    def __init__(
        self,
        repository: DocumentRepository,
        applications: ApplicationService,
        storage: StorageBackend,
        classifier: ClassificationPipeline | None = None,
    ) -> None:
        """Take the repository, the foreign service (ARC-018), storage, and the classifier.

        `classifier` is None whenever `AI_CLASSIFICATION_ENABLED` is off, which
        is what makes AI-024 structural rather than conditional: with the flag
        off the object does not exist, so no client is built and no key is read.
        """
        self._repository = repository
        self._applications = applications
        self._storage = storage
        self._classifier = classifier

    async def list_applications(
        self, session: AsyncSession, user_id: UUID
    ) -> ApplicationListResponse:
        """The borrower's applications, each with a real document count (API-029).

        Here rather than in `applications` for the same reason the checklist
        route is (`2-architecture.md` §5.1): the summary needs one application's
        requirements *and* its documents, and only this domain may query the
        documents table (ARC-009). `applications.service` used to be handed an
        empty map by its own router, so every row in the list read
        "0 of 6 required documents uploaded" however many were actually there.
        """
        application_ids = await self._applications.ids_for_user(session, user_id)
        uploaded = await self._repository.uploaded_types_for(session, application_ids)
        return await self._applications.list_for_user(session, user_id, uploaded)

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
        classifications = await self._repository.classifications_for(session, application_id)
        items = [
            self._to_item(requirement, documents, classifications)
            for requirement in requirements
        ]
        required = [item for item in items if item.required]
        return ChecklistResponse(
            required_count=len(required),
            satisfied_count=sum(1 for item in required if item.satisfied),
            items=items,
        )

    async def upload(
        self,
        session: AsyncSession,
        context: UploadContext,
        upload: UploadRequest,
    ) -> DocumentResponse:
        """Validate, store the blob, write the row, and move the application.

        All three happen in one transaction (API-049, CQ-091): the row and the
        status change commit together, so a request that returns 201 never
        leaves an application whose status disagrees with what was just
        uploaded. A blob written just before a failure is a known, accepted
        gap (VAL-021) — the database stays consistent either way.

        Raises:
            NotFoundError: APPLICATION_NOT_FOUND (API-053).
            DocumentError: UNSUPPORTED_DOCUMENT_TYPE (API-050, decided by
                magic bytes, never by extension); DOCUMENT_EMPTY;
                DOCUMENT_TYPE_NOT_REQUIRED when `doc_type` is not in this
                application's checklist (API-052).
        """
        application_id = context.application_id
        application = await self._applications.get_owned(
            session, application_id, context.user_id
        )
        if application.status not in _UPLOAD_OPEN_STATES:
            raise ApplicationError(code="INVALID_STATE_TRANSITION")
        if len(upload.content) < _MIN_SIZE_BYTES:
            raise DocumentError(code="DOCUMENT_EMPTY", field="file")
        content_type = detect_content_type(upload.content)
        if content_type is None:
            raise DocumentError(code="UNSUPPORTED_DOCUMENT_TYPE", field="file")
        self._assert_required(application, upload.doc_type)

        storage_key = await self._storage.save(application_id, upload.content)
        document = Document(
            id=uuid4(),
            application_id=application_id,
            doc_type=upload.doc_type,
            filename=upload.filename,
            storage_key=storage_key,
            content_type=content_type,
            size_bytes=len(upload.content),
            # Stamped here rather than left to the column default. The default
            # only fills a column, and the entity is built before the insert —
            # so this field was previously None with a `type: ignore` holding
            # the declared type up, which is exactly the kind of hole CQ-020
            # exists to close.
            uploaded_at=datetime.now(UTC),
        )
        created = await self._repository.create(session, document)
        status = await self._recompute(session, application_id)
        await session.commit()
        self._schedule_classification(context, created.id, upload)
        return DocumentResponse(
            id=created.id,
            doc_type=created.doc_type,
            filename=created.filename,
            content_type=created.content_type,
            size_bytes=created.size_bytes,
            uploaded_at=created.uploaded_at,
            application_status=status.value,
        )

    async def download(
        self, session: AsyncSession, application_id: UUID, user_id: UUID, document_id: UUID
    ) -> tuple[bytes, Document]:
        """Fetch a document's bytes, re-checking ownership on every request.

        Never served as a static file (VAL-025): the ownership check here is
        what a static route would skip.

        Raises:
            NotFoundError: APPLICATION_NOT_FOUND, or DOCUMENT_NOT_FOUND when
                the document is not this application's.
        """
        await self._applications.get_owned(session, application_id, user_id)
        document = await self._get_owned_document(session, application_id, document_id)
        content = await self._storage.load(document.storage_key)
        return content, document

    async def delete(
        self, session: AsyncSession, application_id: UUID, user_id: UUID, document_id: UUID
    ) -> DocumentDeleteResponse:
        """Remove a document and recompute the application's status.

        Deleting the last document satisfying a requirement moves the
        application backwards. **This is a normal transition, not an error**
        (API-056, APP-004) — the response makes it visible so the UI can show
        it rather than hide it.
        """
        # Ownership check only: recompute_status re-fetches the application by
        # id, so the entity itself is not needed here.
        await self._applications.get_owned(session, application_id, user_id)
        document = await self._get_owned_document(session, application_id, document_id)
        await self._repository.delete(session, document_id)
        status = await self._recompute(session, application_id)
        await session.commit()
        await self._storage.delete(document.storage_key)
        return DocumentDeleteResponse(application_status=status.value)

    async def _get_owned_document(
        self, session: AsyncSession, application_id: UUID, document_id: UUID
    ) -> Document:
        """Fetch a document, scoped to the application it claims to belong to."""
        document = await self._repository.get(session, document_id)
        if document is None or document.application_id != application_id:
            raise NotFoundError(code="DOCUMENT_NOT_FOUND")
        return document

    def _assert_required(self, application: Application, doc_type: DocumentType) -> None:
        """Reject a doc_type that is not part of this application's checklist.

        `application` is the one the caller already fetched — this must not
        re-query it, or a single upload would resolve ownership twice.
        """
        requirements = self._applications.checklist(application, frozenset())
        if doc_type not in {requirement.doc_type for requirement in requirements}:
            raise DocumentError(code="DOCUMENT_TYPE_NOT_REQUIRED", field="doc_type")

    async def _recompute(
        self, session: AsyncSession, application_id: UUID
    ) -> ApplicationStatus:
        """Refresh and move the application's status from the current uploads."""
        documents = await self._repository.list_for_application(session, application_id)
        uploaded = frozenset(document.doc_type for document in documents)
        return await self._applications.recompute_status(session, application_id, uploaded)

    def _to_item(
        self,
        requirement: DocumentRequirement,
        documents: list[Document],
        classifications: dict[UUID, ClassificationRecord],
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
            documents=[self._to_summary(d, classifications) for d in matching],
        )

    def _to_summary(
        self, document: Document, classifications: dict[UUID, ClassificationRecord]
    ) -> DocumentSummary:
        """Nest one uploaded file, with its advisory classification (AI-025, AI-026).

        The message is composed here, server-side, so the frontend renders a
        string and never implements the decision table. With the classifier off
        there is no record and both fields are null.
        """
        record = classifications.get(document.id)
        return DocumentSummary(
            id=document.id,
            filename=document.filename,
            size_bytes=document.size_bytes,
            uploaded_at=document.uploaded_at,
            classification_status=record.status or None if record else None,
            classification_message=messages.compose(
                record.outcome if record else None,
                record.detected_type if record else None,
                claimed_as_classified(document.doc_type),
            ),
            proposal=_to_proposal_response(record),
        )

    def _schedule_classification(
        self, context: UploadContext, document_id: UUID, upload: UploadRequest
    ) -> None:
        """Queue classification to run after the response (AI-018, AI-019).

        Called only after `session.commit()` has returned: the document row and
        the application status are already durable, so nothing this task does —
        including failing outright — can affect what the borrower was told
        (AI-005).

        With the flag off `self._classifier` is None and this is a no-op,
        leaving the column null. `FastAPI`'s `BackgroundTasks` is enough at this
        size; a broker would be infrastructure for its own sake (AI-019).
        """
        if self._classifier is None:
            return
        context.background_tasks.add_task(
            self._classifier.run, document_id, upload.doc_type, upload.content
        )


def _to_proposal_response(record: ClassificationRecord | None) -> ProposalResponse | None:
    """Surface a document's proposal, or nothing when it made none (T58).

    Absent whenever the classifier did not run, disagreed with what the borrower
    declared, or read no usable figure — all of which mean the same thing to the
    finances form: there is nothing to offer. The pipeline never writes a source
    without at least one figure (`FinancialProposal.is_empty`), so one check
    covers all three.
    """
    if record is None or record.proposal_source is None:
        return None
    return ProposalResponse(
        net_monthly_income=record.proposed_income,
        existing_credit_monthly=record.proposed_credit,
        source=record.proposal_source,
    )
