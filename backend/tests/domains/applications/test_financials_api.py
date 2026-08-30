"""The confirmed financial profile and its assessment. API-073, API-074.

Two things here are worth pointing at. `test_financials_survive_a_borrower_patch`
is the reason this is a table of its own rather than columns on `borrowers`
(API-037 replaces that collection wholesale, DOM-029). And
`test_put_records_manual_provenance` pins that the client cannot assert where a
figure came from — the server records it, or the audit trail is self-reported
and worthless.
"""

_CREDENTIALS = {"email": "financials@example.com", "password": "hunter2hunter2"}

_PRIMARY_SIMULATION = {
    "property_value": "300000.00",
    "own_contribution": "30000.00",
    "term_months": 300,
    "annual_nominal_rate": "0.0400",
    "region": "FLANDERS",
    "is_first_home": True,
}

_BORROWER = {
    "full_name": "Jan Test",
    "date_of_birth": "1990-04-12",
    "employment_type": "EMPLOYEE",
    "monthly_net_income": "3200.00",
    "has_existing_credit": False,
}


async def _application_with_simulation(client) -> str:
    """Sign up, run the AC-003 simulation, and open a draft seeded from it."""
    simulation = (await client.post("/api/simulations", json=_PRIMARY_SIMULATION)).json()
    await client.post("/api/auth/signup", json={**_CREDENTIALS, "simulation_id": simulation["id"]})
    created = await client.post("/api/applications", json={"simulation_id": simulation["id"]})
    application_id: str = created.json()["id"]
    return application_id


async def test_get_financials_is_empty_before_anything_is_saved(client, engine):
    application_id = await _application_with_simulation(client)

    response = await client.get(f"/api/applications/{application_id}/financials")

    assert response.status_code == 200
    body = response.json()
    assert body["net_monthly_income"] is None
    assert body["existing_credit_monthly"] is None
    assert body["dependants"] == 0
    assert body["updated_at"] is None
    # There is a loan to measure against, so an assessment is returned — it just
    # has no income to work with (SIM-027).
    assert body["assessment"]["band"] == "INSUFFICIENT_DATA"
    assert body["assessment"]["dsti"] is None
    assert body["assessment"]["residual_floor"] == "1200.00"


async def test_put_records_manual_provenance(client, engine):
    """DOM-029. The client sends values; the server decides how they arrived."""
    application_id = await _application_with_simulation(client)

    response = await client.put(
        f"/api/applications/{application_id}/financials",
        json={"net_monthly_income": "4800.00", "dependants": 0},
    )

    assert response.status_code == 200
    income = response.json()["net_monthly_income"]
    assert income["amount"] == "4800.00"
    assert income["provenance"] == "MANUAL"
    assert income["source_document_id"] is None
    assert income["confirmed_at"] is not None


async def test_put_rejects_a_client_supplied_provenance(client, engine):
    """A self-reported audit trail is not an audit trail (extra="forbid")."""
    application_id = await _application_with_simulation(client)

    response = await client.put(
        f"/api/applications/{application_id}/financials",
        json={"net_monthly_income": "4800.00", "provenance": "DOCUMENT"},
    )

    assert response.status_code == 422


async def test_put_returns_the_assessment_for_the_saved_figures(client, engine):
    """AC-009 over the wire, against AC-003's monthly payment of 1414.52."""
    application_id = await _application_with_simulation(client)

    response = await client.put(
        f"/api/applications/{application_id}/financials",
        json={"net_monthly_income": "4800.00", "dependants": 0},
    )

    assessment = response.json()["assessment"]
    assert assessment["monthly_obligations"] == "1414.52"
    assert assessment["dsti"] == "0.2947"
    assert assessment["residual_income"] == "3385.48"
    assert assessment["band"] == "COMFORTABLE"


async def test_put_counts_existing_credit_towards_the_obligations(client, engine):
    application_id = await _application_with_simulation(client)

    response = await client.put(
        f"/api/applications/{application_id}/financials",
        json={"net_monthly_income": "4800.00", "existing_credit_monthly": "450.00"},
    )

    assessment = response.json()["assessment"]
    assert assessment["monthly_obligations"] == "1864.52"
    assert assessment["band"] == "TIGHT"


async def test_put_replaces_the_profile_wholesale(client, engine):
    """API-037's semantics, applied here too: the form sends every field."""
    application_id = await _application_with_simulation(client)
    await client.put(
        f"/api/applications/{application_id}/financials",
        json={"net_monthly_income": "4800.00", "existing_credit_monthly": "450.00"},
    )

    response = await client.put(
        f"/api/applications/{application_id}/financials",
        json={"net_monthly_income": "4800.00"},
    )

    assert response.json()["existing_credit_monthly"] is None


async def test_financials_survive_a_borrower_patch(client, engine):
    """DOM-029, the reason this is not columns on `borrowers`.

    A PATCH replaces the borrower collection wholesale (API-037). A confirmed
    income stored on that row would be destroyed by the borrower editing their
    own name — which is exactly the bug this table exists to avoid.
    """
    application_id = await _application_with_simulation(client)
    await client.put(
        f"/api/applications/{application_id}/financials",
        json={"net_monthly_income": "4800.00", "dependants": 2},
    )

    await client.patch(
        f"/api/applications/{application_id}",
        json={"borrowers": [{**_BORROWER, "full_name": "Jan Renamed"}]},
    )

    response = await client.get(f"/api/applications/{application_id}/financials")
    assert response.json()["net_monthly_income"]["amount"] == "4800.00"
    assert response.json()["dependants"] == 2


async def test_assessment_is_absent_without_a_linked_simulation(client, engine):
    """No instalment to measure against, and inventing one would be worse."""
    await client.post("/api/auth/signup", json=_CREDENTIALS)
    created = (await client.post("/api/applications", json={})).json()

    response = await client.put(
        f"/api/applications/{created['id']}/financials",
        json={"net_monthly_income": "4800.00"},
    )

    assert response.status_code == 200
    assert response.json()["assessment"] is None
    assert response.json()["net_monthly_income"]["amount"] == "4800.00"


async def test_another_users_financials_return_404_not_403(client, engine):
    """AUTH-035. Ownership is checked before anything is read or written."""
    application_id = await _application_with_simulation(client)
    await client.post("/api/auth/logout")
    await client.post(
        "/api/auth/signup", json={"email": "other@example.com", "password": "hunter2hunter2"}
    )

    read = await client.get(f"/api/applications/{application_id}/financials")
    written = await client.put(
        f"/api/applications/{application_id}/financials", json={"net_monthly_income": "9000.00"}
    )

    assert read.status_code == 404
    assert written.status_code == 404
    assert read.json()["code"] == "APPLICATION_NOT_FOUND"


async def test_put_rejects_a_negative_income(client, engine):
    application_id = await _application_with_simulation(client)

    response = await client.put(
        f"/api/applications/{application_id}/financials",
        json={"net_monthly_income": "-100.00"},
    )

    assert response.status_code == 422
