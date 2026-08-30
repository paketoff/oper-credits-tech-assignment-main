"""Classification, after the upload has already succeeded (AI-018 – AI-024).

**Nothing here can affect the upload.** It runs as a background task scheduled
once the transaction has committed and the 201 has been returned, so the
borrower is already done. If it fails, times out, or the API is unreachable,
the document is still stored, the checklist still counts it, and the
application status is still whatever the upload made it (AI-005).

The status column answers "did this run"; the outcome column answers "what did
it decide", and is only ever written together with `DONE`.
"""

import logging
from enum import StrEnum
from uuid import UUID

from app.core.database import background_session
from app.core.enums import DocumentType
from app.domains.documents.classification import evaluator
from app.domains.documents.classification.client import (
    ClassificationClient,
    ClassificationError,
    render_first_page,
)
from app.domains.documents.classification.entities import ClassificationOutcome
from app.domains.documents.extraction.proposal import to_proposal
from app.domains.documents.file_type import detect_content_type
from app.domains.documents.repository import ClassificationRecord, DocumentRepository

_logger = logging.getLogger(__name__)


class ClassificationStatus(StrEnum):
    """Whether classification ran, independently of what it decided (AI-020).

    `FAILED` and `SKIPPED` are distinct in the database and identical to the
    borrower — both render as nothing (AI-021). A failed classification is our
    problem, not theirs, and a disabled feature is not news.
    """

    PENDING = "PENDING"
    DONE = "DONE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ClassificationPipeline:
    """Runs one classification and records the result.

    Constructed only when the feature flag is on, which is what makes AI-024
    true structurally: with the flag off this object does not exist, so no
    client is built and no key is read.
    """

    def __init__(self, client: ClassificationClient, repository: DocumentRepository) -> None:
        """Take the client and the repository; the session is this task's own."""
        self._client = client
        self._repository = repository

    async def run(self, document_id: UUID, claimed: DocumentType, content: bytes) -> None:
        """Classify one uploaded document and store the verdict.

        Args:
            document_id: The row to annotate.
            claimed: What the borrower said the file was. The comparison, and
                the authority, stay with them (AI-006).
            content: The uploaded bytes, held in memory for the length of this
                call and never written to disk as a separate artefact (AI-031).

        Never raises. Any failure is recorded as `FAILED` and stopped here
        (AI-023): this runs after the response, so there is nobody left to tell.
        """
        try:
            page = render_first_page(content, _content_type_of(content))
            verdict, fields = await self._client.classify(page, claimed)
            outcome = evaluator.evaluate(verdict, claimed)
        except ClassificationError:
            # The document id and nothing else: never the image, the filename,
            # the model's reason, or any text from the page (AI-028).
            _logger.warning("classification failed", extra={"document_id": str(document_id)})
            await self._record(_failed(document_id))
            return
        except Exception:
            _logger.exception("classification errored", extra={"document_id": str(document_id)})
            await self._record(_failed(document_id))
            return

        # T57. Extracted fields are trusted **only** when classification agreed:
        # numbers read off a document that turned out to be something else
        # describe the wrong document. One condition, and it is the whole reason
        # the two questions can safely share a call.
        proposal = (
            to_proposal(claimed, fields)
            if outcome is ClassificationOutcome.CONFIRMED and fields is not None
            else None
        )
        # A proposal that reads nothing is not a proposal. Deciding that here,
        # once, is what keeps the read side from having to re-derive it.
        if proposal is not None and proposal.is_empty():
            proposal = None
        await self._record(
            ClassificationRecord(
                document_id=document_id,
                status=ClassificationStatus.DONE.value,
                outcome=outcome.value,
                detected_type=verdict.doc_type.value,
                proposed_income=proposal.net_monthly_income if proposal else None,
                proposed_credit=proposal.existing_credit_monthly if proposal else None,
                proposal_source=proposal.source if proposal else None,
            )
        )

    async def _record(self, record: ClassificationRecord) -> None:
        """Write the result in this task's own session, and commit it."""
        async with background_session() as session:
            await self._repository.set_classification(session, record)
            await session.commit()


def _content_type_of(content: bytes) -> str:
    """Re-detect the type from the bytes rather than trusting a passed-in string.

    The same magic-byte check the upload already used (VAL-022). Cheap, and it
    keeps this task independent of what the caller believed.
    """
    return detect_content_type(content) or "application/octet-stream"


def _failed(document_id: UUID) -> ClassificationRecord:
    """The row to write when classification could not complete (AI-023)."""
    return ClassificationRecord(
        document_id=document_id, status=ClassificationStatus.FAILED.value, outcome=None
    )
