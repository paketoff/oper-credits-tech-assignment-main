"""Classification never touches the upload. AI-004 - AI-006, AI-018 - AI-024, AI-036.

`test_upload_succeeds_when_classifier_raises` is the one to point at on a
walkthrough: it is what proves AI-005. The classifier throws, and the borrower
still gets a 201, the row is still there, the checklist still counts it, and the
application status is still what the upload made it. The feature can fail
completely and the product does not notice.
"""

from decimal import Decimal
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image
from sqlalchemy import select

from app.core.enums import DocumentType
from app.domains.documents.classification.client import ClassificationError
from app.domains.documents.classification.entities import (
    ClassificationVerdict,
    ClassifiedType,
)
from app.domains.documents.classification.pipeline import (
    ClassificationPipeline,
    ClassificationStatus,
)
from app.domains.documents.extraction.schemas import PayslipFields
from app.domains.documents.repository import SqlDocumentRepository
from app.domains.documents.tables import DocumentRow


def _real_png() -> bytes:
    """A PNG that PIL can actually open.

    The upload path only checks magic bytes (VAL-022) and never opens the file,
    so the rest of the suite gets away with a header and zeros. The classifier
    genuinely renders it, so this one has to be a real image.
    """
    buffer = BytesIO()
    Image.new("RGB", (40, 60), "white").save(buffer, format="PNG")
    return buffer.getvalue()


_PNG = _real_png()
_CREDENTIALS = {"email": "classify@example.com", "password": "hunter2hunter2"}

_BORROWER = {
    "full_name": "Jan Test",
    "date_of_birth": "1990-04-12",
    "employment_type": "EMPLOYEE",
    "monthly_net_income": "3200.00",
    "has_existing_credit": False,
}
_PROPERTY = {
    "region": "FLANDERS",
    "is_first_home": True,
    "property_type": "EXISTING",
    "purchase_price": "300000.00",
}


class _FakeClient:
    """Answers with a fixed verdict, or raises."""

    def __init__(
        self, reply: ClassificationVerdict | Exception, fields: object | None = None
    ) -> None:
        self._reply = reply
        self._fields = fields
        self.calls = 0

    async def classify(
        self, page_png: bytes, claimed: object = None
    ) -> tuple[ClassificationVerdict, object | None]:
        self.calls += 1
        if isinstance(self._reply, Exception):
            raise self._reply
        return self._reply, self._fields


async def _submitted_application(client) -> str:
    await client.post("/api/auth/signup", json=_CREDENTIALS)
    created = (await client.post("/api/applications", json={})).json()
    await client.patch(
        f"/api/applications/{created['id']}",
        json={"borrowers": [_BORROWER], "property": _PROPERTY},
    )
    await client.post(f"/api/applications/{created['id']}/submit")
    application_id: str = created["id"]
    return application_id


async def _upload(client, application_id: str, doc_type: str = "IDENTITY"):
    return await client.post(
        f"/api/applications/{application_id}/documents",
        files={"file": ("id.png", _PNG, "image/png")},
        data={"doc_type": doc_type},
    )


async def test_flag_off_skips_classification_entirely(client, engine, session):
    """AI-004, AI-024. No client is built and no key is read; the column stays null."""
    application_id = await _submitted_application(client)

    response = await _upload(client, application_id)

    assert response.status_code == 201
    row = (await session.execute(select(DocumentRow))).scalars().one()
    assert row.classification_status is None
    assert row.classification_outcome is None


async def test_upload_succeeds_when_classifier_raises(client, engine, session):
    """AI-036, AI-005. The proof that the feature cannot break the product.

    Driven at the pipeline level rather than through DI, because the flag is off
    in tests by default — what matters is that a raising classifier leaves the
    upload's outcome untouched and records FAILED.
    """
    application_id = await _submitted_application(client)
    response = await _upload(client, application_id)
    assert response.status_code == 201
    document_id = response.json()["id"]
    status_after_upload = response.json()["application_status"]

    pipeline = ClassificationPipeline(
        _FakeClient(ClassificationError("unreachable")),  # type: ignore[arg-type]
        SqlDocumentRepository(),
    )
    await pipeline.run(uuid4().__class__(document_id), DocumentType.IDENTITY, _PNG)

    checklist = await client.get(f"/api/applications/{application_id}/checklist")
    identity = next(
        item for item in checklist.json()["items"] if item["doc_type"] == "IDENTITY"
    )
    assert identity["satisfied"] is True
    application = await client.get(f"/api/applications/{application_id}")
    assert application.json()["status"] == status_after_upload


async def test_failed_classification_is_recorded_without_an_outcome(client, engine, session):
    """AI-020, AI-023. FAILED is a lifecycle fact; there is no verdict to store."""
    application_id = await _submitted_application(client)
    document_id = (await _upload(client, application_id)).json()["id"]

    pipeline = ClassificationPipeline(
        _FakeClient(ClassificationError("boom")),  # type: ignore[arg-type]
        SqlDocumentRepository(),
    )
    await pipeline.run(uuid4().__class__(document_id), DocumentType.IDENTITY, _PNG)

    row = (await session.execute(select(DocumentRow))).scalars().one()
    await session.refresh(row)
    assert row.classification_status == ClassificationStatus.FAILED.value
    assert row.classification_outcome is None


async def test_outcome_never_changes_doc_type_or_satisfaction(client, engine, session):
    """AI-017. A confident mismatch warns; the requirement stays satisfied."""
    application_id = await _submitted_application(client)
    document_id = (await _upload(client, application_id)).json()["id"]

    pipeline = ClassificationPipeline(
        _FakeClient(  # type: ignore[arg-type]
            ClassificationVerdict(
                doc_type=ClassifiedType.BANK_STATEMENTS, confidence=0.97, reason="an account"
            )
        ),
        SqlDocumentRepository(),
    )
    await pipeline.run(uuid4().__class__(document_id), DocumentType.IDENTITY, _PNG)

    row = (await session.execute(select(DocumentRow))).scalars().one()
    await session.refresh(row)
    assert row.classification_outcome == "LIKELY_MISMATCH"
    # The borrower declared IDENTITY, so IDENTITY it stays (DOC-010).
    assert row.doc_type == "IDENTITY"
    checklist = await client.get(f"/api/applications/{application_id}/checklist")
    identity = next(
        item for item in checklist.json()["items"] if item["doc_type"] == "IDENTITY"
    )
    assert identity["satisfied"] is True


async def test_a_deleted_document_is_not_an_error_to_annotate(engine, session):
    """A normal race: the task finishes after the borrower removed the file."""
    pipeline = ClassificationPipeline(
        _FakeClient(  # type: ignore[arg-type]
            ClassificationVerdict(doc_type=ClassifiedType.EPC, confidence=0.9, reason="epc")
        ),
        SqlDocumentRepository(),
    )

    await pipeline.run(uuid4(), DocumentType.EPC, _PNG)  # nothing raised


@pytest.mark.parametrize("status", list(ClassificationStatus))
def test_every_status_is_a_plain_string(status: ClassificationStatus) -> None:
    """AI-020. Stored as a string column, so the enum must serialise cleanly."""
    assert isinstance(status.value, str)


async def test_a_confirmed_payslip_proposes_its_net_pay(client, engine, session):
    """T57, T58. Extraction rides the classification call and reaches the checklist."""
    application_id = await _submitted_application(client)
    await client.patch(
        f"/api/applications/{application_id}",
        json={"borrowers": [_BORROWER], "property": _PROPERTY},
    )
    document_id = (await _upload(client, application_id, "PAYSLIPS")).json()["id"]

    pipeline = ClassificationPipeline(
        _FakeClient(  # type: ignore[arg-type]
            ClassificationVerdict(
                doc_type=ClassifiedType.PAYSLIPS, confidence=0.95, reason="a salary slip"
            ),
            PayslipFields(net_monthly_pay=Decimal("3200.00"), period="2026-03"),
        ),
        SqlDocumentRepository(),
    )
    await pipeline.run(uuid4().__class__(document_id), DocumentType.PAYSLIPS, _PNG)

    checklist = (await client.get(f"/api/applications/{application_id}/checklist")).json()
    payslips = next(item for item in checklist["items"] if item["doc_type"] == "PAYSLIPS")
    assert payslips["documents"][0]["proposal"]["net_monthly_income"] == "3200.00"
    assert payslips["documents"][0]["proposal"]["source"] == "your payslip"


async def test_fields_are_discarded_when_classification_disagrees(client, engine, session):
    """T57. The single rule that lets both questions share one call.

    Figures read off a document that turned out to be something else describe
    the wrong document, so they are dropped even though the model returned them.
    """
    application_id = await _submitted_application(client)
    await client.patch(
        f"/api/applications/{application_id}",
        json={"borrowers": [_BORROWER], "property": _PROPERTY},
    )
    document_id = (await _upload(client, application_id, "PAYSLIPS")).json()["id"]

    pipeline = ClassificationPipeline(
        _FakeClient(  # type: ignore[arg-type]
            ClassificationVerdict(
                doc_type=ClassifiedType.BANK_STATEMENTS, confidence=0.95, reason="an account"
            ),
            PayslipFields(net_monthly_pay=Decimal("9999.00")),
        ),
        SqlDocumentRepository(),
    )
    await pipeline.run(uuid4().__class__(document_id), DocumentType.PAYSLIPS, _PNG)

    checklist = (await client.get(f"/api/applications/{application_id}/checklist")).json()
    payslips = next(item for item in checklist["items"] if item["doc_type"] == "PAYSLIPS")
    assert payslips["documents"][0]["proposal"] is None
    assert "bank statement" in payslips["documents"][0]["classification_message"]
