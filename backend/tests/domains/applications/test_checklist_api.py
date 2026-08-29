"""GET /api/applications/{id}/checklist. API-045 - API-047, DOC-005 - DOC-011.

Lives in documents/router.py, not applications/ — ARC-009 keeps the documents
table off limits to applications, and the checklist needs both.
"""

_CREDENTIALS_A = {"email": "checklist-a@example.com", "password": "hunter2hunter2"}
_CREDENTIALS_B = {"email": "checklist-b@example.com", "password": "hunter2hunter2"}


async def _draft_with_property(client, employment: str = "EMPLOYEE") -> dict:
    created = (await client.post("/api/applications", json={})).json()
    await client.patch(
        f"/api/applications/{created['id']}",
        json={
            "borrowers": [
                {
                    "full_name": "Jan Test",
                    "date_of_birth": "1990-04-12",
                    "employment_type": employment,
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
    return created


async def test_checklist_returns_counts_and_items(client, engine):
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application = await _draft_with_property(client)

    response = await client.get(f"/api/applications/{application['id']}/checklist")

    assert response.status_code == 200
    body = response.json()
    # base 3 + payslips + employer statement + EPC (existing property) = 6.
    assert body["required_count"] == 6
    assert body["satisfied_count"] == 0
    assert {item["doc_type"] for item in body["items"]} >= {"IDENTITY", "PAYSLIPS", "EPC"}


async def test_conditional_item_carries_reason(client, engine):
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application = await _draft_with_property(client)

    response = await client.get(f"/api/applications/{application['id']}/checklist")

    by_type = {item["doc_type"]: item for item in response.json()["items"]}
    assert by_type["IDENTITY"]["reason"] is None
    assert by_type["PAYSLIPS"]["reason"] == "Required because you selected employed"


async def test_changing_employment_type_changes_checklist_response(client, engine):
    # SCP-022, UX-038: the product point of the whole build.
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application = await _draft_with_property(client, employment="EMPLOYEE")
    employee_types = {
        item["doc_type"]
        for item in (
            await client.get(f"/api/applications/{application['id']}/checklist")
        ).json()["items"]
    }

    await client.patch(
        f"/api/applications/{application['id']}",
        json={
            "borrowers": [
                {
                    "full_name": "Jan Test",
                    "date_of_birth": "1990-04-12",
                    "employment_type": "SELF_EMPLOYED",
                    "monthly_net_income": "3200.00",
                    "has_existing_credit": False,
                }
            ]
        },
    )
    self_employed_types = {
        item["doc_type"]
        for item in (
            await client.get(f"/api/applications/{application['id']}/checklist")
        ).json()["items"]
    }

    assert employee_types != self_employed_types
    assert "PAYSLIPS" in employee_types
    assert "TAX_ASSESSMENT" in self_employed_types


async def test_checklist_of_other_users_application_returns_404(client, engine):
    await client.post("/api/auth/signup", json=_CREDENTIALS_A)
    application = await _draft_with_property(client)
    await client.post("/api/auth/logout")
    await client.post("/api/auth/signup", json=_CREDENTIALS_B)

    response = await client.get(f"/api/applications/{application['id']}/checklist")

    assert response.status_code == 404
    assert response.json()["code"] == "APPLICATION_NOT_FOUND"
