"""Upload, download, delete. API-048 - API-056, VAL-022 - VAL-025."""

_PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\nsome content padding to be realistic"
_CREDENTIALS_A = {"email": "docs-a@example.com", "password": "hunter2hunter2"}
_CREDENTIALS_B = {"email": "docs-b@example.com", "password": "hunter2hunter2"}


async def _submitted_application(client) -> str:
    """A signed-up user with an application in DOCUMENTS_PENDING."""
    created = (await client.post("/api/applications", json={})).json()
    await client.patch(
        f"/api/applications/{created['id']}",
        json={
            "borrowers": [
                {
                    "full_name": "Jan Test",
                    "date_of_birth": "1990-04-12",
                    "employment_type": "EMPLOYEE",
                    "monthly_net_income": "3200.00",
                    "has_existing_credit": False,
                }
            ],
            "property": {
                "region": "FLANDERS",
                "is_first_home": True,
                "property_type": "EXISTING",
                "purchase_price": "300000.00",
            },
        },
    )
    await client.post(f"/api/applications/{created['id']}/submit")
    return created["id"]


async def _upload(client, application_id: str, doc_type: str, content: bytes):
    return await client.post(
        f"/api/applications/{application_id}/documents",
        data={"doc_type": doc_type},
        files={"file": (f"{doc_type.lower()}.pdf", content)},
    )


async def test_upload_pdf_succeeds_and_returns_application_status(client, engine):
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application_id = await _submitted_application(client)

    response = await _upload(client, application_id, "IDENTITY", _PDF)

    assert response.status_code == 201
    body = response.json()
    assert body["doc_type"] == "IDENTITY"
    assert body["filename"] == "identity.pdf"
    assert body["content_type"] == "application/pdf"
    assert body["application_status"] == "DOCUMENTS_PENDING"


async def test_upload_txt_renamed_as_pdf_is_rejected_415(client, engine):
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application_id = await _submitted_application(client)

    response = await _upload(client, application_id, "IDENTITY", b"just plain text")

    assert response.status_code == 415
    assert response.json()["code"] == "UNSUPPORTED_DOCUMENT_TYPE"


async def test_upload_oversize_rejected_413_before_buffering(client, engine):
    # VAL-024: the body-size middleware, not this handler, is what answers.
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application_id = await _submitted_application(client)
    oversized = _PDF + b"x" * (10 * 1024 * 1024 + 1)

    response = await _upload(client, application_id, "IDENTITY", oversized)

    assert response.status_code == 413
    assert response.json()["code"] == "DOCUMENT_TOO_LARGE"


async def test_upload_empty_file_rejected_422(client, engine):
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application_id = await _submitted_application(client)

    response = await _upload(client, application_id, "IDENTITY", b"")

    assert response.status_code == 422
    assert response.json()["code"] == "DOCUMENT_EMPTY"


async def test_upload_type_not_in_checklist_rejected_422(client, engine):
    # BUILDING_PERMIT belongs to a NEW_BUILD checklist; this application is
    # EXISTING (see _submitted_application), so it is not required here.
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application_id = await _submitted_application(client)

    response = await _upload(client, application_id, "BUILDING_PERMIT", _PDF)

    assert response.status_code == 422
    assert response.json()["code"] == "DOCUMENT_TYPE_NOT_REQUIRED"


async def test_upload_and_status_change_share_one_transaction(client, engine):
    # CQ-091, API-049: uploading every required document moves the application
    # to DOCUMENTS_COMPLETE in the same response that reports the upload.
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application_id = await _submitted_application(client)
    checklist = (await client.get(f"/api/applications/{application_id}/checklist")).json()
    required_types = [item["doc_type"] for item in checklist["items"] if item["required"]]

    last_response = None
    for doc_type in required_types:
        last_response = await _upload(client, application_id, doc_type, _PDF)

    assert last_response is not None
    assert last_response.json()["application_status"] == "DOCUMENTS_COMPLETE"


async def test_delete_last_satisfying_document_returns_pending(client, engine):
    # API-056, APP-004: a normal transition, not an error.
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application_id = await _submitted_application(client)
    checklist = (await client.get(f"/api/applications/{application_id}/checklist")).json()
    required_types = [item["doc_type"] for item in checklist["items"] if item["required"]]
    uploaded_ids = []
    for doc_type in required_types:
        response = await _upload(client, application_id, doc_type, _PDF)
        uploaded_ids.append(response.json()["id"])
    assert (
        await client.get(f"/api/applications/{application_id}")
    ).json()["status"] == "DOCUMENTS_COMPLETE"

    response = await client.delete(
        f"/api/applications/{application_id}/documents/{uploaded_ids[0]}"
    )

    assert response.status_code == 200
    assert response.json()["application_status"] == "DOCUMENTS_PENDING"


async def test_download_of_other_users_document_returns_404(client, engine):
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application_id = await _submitted_application(client)
    uploaded = (await _upload(client, application_id, "IDENTITY", _PDF)).json()
    await client.post("/api/auth/logout")
    await client.post("/api/auth/signup", json=_CREDENTIALS_B)

    response = await client.get(
        f"/api/applications/{application_id}/documents/{uploaded['id']}"
    )

    assert response.status_code == 404
    assert response.json()["code"] == "APPLICATION_NOT_FOUND"


async def test_upload_before_submission_is_rejected(client, engine):
    # VAL-013: application state must not be SUBMITTED (i.e. still DRAFT)
    # before documents open, nor WITHDRAWN.
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    created = (await client.post("/api/applications", json={})).json()

    response = await _upload(client, created["id"], "IDENTITY", _PDF)

    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATE_TRANSITION"


async def test_downloaded_bytes_round_trip(client, engine):
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application_id = await _submitted_application(client)
    uploaded = (await _upload(client, application_id, "IDENTITY", _PDF)).json()

    response = await client.get(
        f"/api/applications/{application_id}/documents/{uploaded['id']}"
    )

    assert response.status_code == 200
    assert response.content == _PDF
    assert "attachment" in response.headers["content-disposition"]


async def test_the_summary_list_counts_the_documents_actually_uploaded(client, engine):
    # The list route used to live in applications/router.py, which had no way
    # to reach the documents table and passed an empty map. Every row read
    # "0 of 6 required documents uploaded" no matter how many were there, and
    # nothing caught it: no test had ever listed an application that had any.
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application_id = await _submitted_application(client)
    await _upload(client, application_id, "IDENTITY", _PDF)
    await _upload(client, application_id, "BANK_STATEMENTS", _PDF)

    listed = (await client.get("/api/applications")).json()["items"][0]

    assert listed["documents_satisfied"] == 2
    assert listed["documents_required"] == 6
