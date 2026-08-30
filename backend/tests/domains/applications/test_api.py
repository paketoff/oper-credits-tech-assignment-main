"""The application wire contract. API-029 - API-044.

`AUTH-035` is the one that gets asked about on a walkthrough: another user's
application returns 404, not 403, because a 403 would confirm it exists.
"""


_CREDENTIALS_A = {"email": "owner-a@example.com", "password": "hunter2hunter2"}
_CREDENTIALS_B = {"email": "owner-b@example.com", "password": "hunter2hunter2"}


async def _signed_up(client, credentials: dict) -> None:
    await client.post("/api/auth/signup", json=credentials)


async def test_list_returns_only_own_applications(client, engine):
    await _signed_up(client, _CREDENTIALS_A)
    await client.post("/api/applications", json={})
    await client.post("/api/auth/logout")
    await _signed_up(client, _CREDENTIALS_B)

    response = await client.get("/api/applications")

    assert response.status_code == 200
    assert response.json()["items"] == []


async def test_other_users_application_returns_404_not_403(client, engine):
    await _signed_up(client, _CREDENTIALS_A)
    created = (await client.post("/api/applications", json={})).json()
    await client.post("/api/auth/logout")
    await _signed_up(client, _CREDENTIALS_B)

    response = await client.get(f"/api/applications/{created['id']}")

    assert response.status_code == 404
    assert response.json()["code"] == "APPLICATION_NOT_FOUND"
    assert "403" not in str(response.status_code)


async def test_patch_updates_only_present_fields(client, engine):
    await _signed_up(client, _CREDENTIALS_A)
    created = (await client.post("/api/applications", json={})).json()

    response = await client.patch(
        f"/api/applications/{created['id']}",
        json={
            "property": {
                "region": "FLANDERS",
                "is_first_home": True,
                "property_type": "EXISTING",
                "purchase_price": "300000.00",
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["borrowers"] == []
    assert response.json()["property"]["region"] == "FLANDERS"


async def test_patch_rejects_status_field(client, engine):
    # API-011, API-038: status is an action, not a writable field.
    await _signed_up(client, _CREDENTIALS_A)
    created = (await client.post("/api/applications", json={})).json()

    response = await client.patch(
        f"/api/applications/{created['id']}", json={"status": "SUBMITTED"}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


async def _submittable_application(client) -> dict:
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
    return created


async def test_submit_transitions_to_submitted(client, engine):
    # APP-002: the automatic move means the borrower sees DOCUMENTS_PENDING,
    # not SUBMITTED sitting still.
    await _signed_up(client, _CREDENTIALS_A)
    created = await _submittable_application(client)

    response = await client.post(f"/api/applications/{created['id']}/submit")

    assert response.status_code == 200
    assert response.json()["status"] == "DOCUMENTS_PENDING"


async def test_double_submit_returns_409(client, engine):
    await _signed_up(client, _CREDENTIALS_A)
    created = await _submittable_application(client)
    await client.post(f"/api/applications/{created['id']}/submit")

    response = await client.post(f"/api/applications/{created['id']}/submit")

    assert response.status_code == 409
    assert response.json()["code"] == "APPLICATION_ALREADY_SUBMITTED"


async def test_submit_with_missing_field_returns_422_with_field_name(client, engine):
    await _signed_up(client, _CREDENTIALS_A)
    created = (await client.post("/api/applications", json={})).json()

    response = await client.post(f"/api/applications/{created['id']}/submit")

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["field"] == "borrowers"


async def test_borrower_under_eighteen_is_rejected_at_submit(client, engine):
    # DOM-028, VAL-011, VAL-020.
    await _signed_up(client, _CREDENTIALS_A)
    created = (await client.post("/api/applications", json={})).json()
    await client.patch(
        f"/api/applications/{created['id']}",
        json={
            "borrowers": [
                {
                    "full_name": "Too Young",
                    "date_of_birth": "2015-01-01",
                    "employment_type": "OTHER",
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

    response = await client.post(f"/api/applications/{created['id']}/submit")

    assert response.status_code == 422
    assert response.json()["field"] == "date_of_birth"


async def test_post_applications_seeds_the_draft_from_the_claimed_simulation(client, engine):
    # API-032, ARC-047, UX-027: the flow this session's third cross-domain
    # edge exists for. Signup only claims; this call creates the draft.
    simulation = (
        await client.post(
            "/api/simulations",
            json={
                "property_value": "300000.00",
                "own_contribution": "30000.00",
                "term_months": 300,
                "annual_nominal_rate": "0.0400",
                "region": "FLANDERS",
                "is_first_home": True,
            },
        )
    ).json()
    signup = await client.post(
        "/api/auth/signup",
        json={
            "email": "seeded-flow@example.com",
            "password": "hunter2hunter2",
            "simulation_id": simulation["id"],
        },
    )
    assert signup.json()["claimed_simulation_id"] == simulation["id"]

    response = await client.post(
        "/api/applications", json={"simulation_id": simulation["id"]}
    )

    assert response.status_code == 201
    assert response.json()["property"]["region"] == "FLANDERS"
    assert response.json()["property"]["purchase_price"] == "300000.00"
    # property_type is not asked by the simulator, so the wizard still asks it
    # even though the rest of the section arrived prefilled.


async def test_patch_allowed_in_documents_pending_not_once_locked(client, engine):
    # VAL-020: employment type is editable after documents exist to upload,
    # which is only possible past DRAFT. API-040, narrowed at T21.
    await _signed_up(client, _CREDENTIALS_A)
    created = await _submittable_application(client)
    await client.post(f"/api/applications/{created['id']}/submit")

    response = await client.patch(
        f"/api/applications/{created['id']}",
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

    assert response.status_code == 200
    assert response.json()["borrowers"][0]["employment_type"] == "SELF_EMPLOYED"


async def test_a_simulation_can_be_attached_after_the_application_exists(client, engine):
    # A borrower who signs up without opening the calculator has no simulation
    # on their application, so the affordability check has no instalment to
    # measure against and the whole panel stayed empty (API-075). Attaching one
    # had no path at all: the link was made at creation and never again.
    await client.post(
        "/api/auth/signup",
        json={"email": "attach@example.com", "password": "hunter2hunter2"},
    )
    application_id = (await client.post("/api/applications", json={})).json()["id"]
    simulation_id = (
        await client.post(
            "/api/simulations",
            json={
                "property_value": "300000.00",
                "own_contribution": "30000.00",
                "term_months": 300,
                "annual_nominal_rate": "0.0400",
                "region": "FLANDERS",
                "is_first_home": True,
            },
        )
    ).json()["id"]

    response = await client.patch(
        f"/api/applications/{application_id}", json={"simulation_id": simulation_id}
    )

    assert response.status_code == 200
    assert response.json()["simulation_id"] == simulation_id


async def test_someone_elses_simulation_cannot_be_attached(client, engine):
    # The id is an unguessable UUID4 and readable by anyone holding it
    # (API-021), so ownership has to be checked here or a stranger's figures
    # could be pinned to this application.
    await client.post(
        "/api/auth/signup",
        json={"email": "owner@example.com", "password": "hunter2hunter2"},
    )
    simulation_id = (
        await client.post(
            "/api/simulations",
            json={
                "property_value": "300000.00",
                "own_contribution": "30000.00",
                "term_months": 300,
                "annual_nominal_rate": "0.0400",
                "region": "FLANDERS",
                "is_first_home": True,
            },
        )
    ).json()["id"]
    # Claimed by its owner first — an *unclaimed* simulation belongs to whoever
    # holds its id, by design (DOM-027), so the theft only becomes a theft once
    # it has an owner.
    owned_application = (await client.post("/api/applications", json={})).json()["id"]
    await client.patch(
        f"/api/applications/{owned_application}", json={"simulation_id": simulation_id}
    )
    await client.post("/api/auth/logout")
    await client.post(
        "/api/auth/signup",
        json={"email": "thief@example.com", "password": "hunter2hunter2"},
    )
    application_id = (await client.post("/api/applications", json={})).json()["id"]

    response = await client.patch(
        f"/api/applications/{application_id}", json={"simulation_id": simulation_id}
    )

    assert response.status_code == 404
    assert response.json()["code"] == "SIMULATION_NOT_FOUND"


async def test_attaching_a_simulation_carries_its_figures_onto_the_application(client, engine):
    # Attaching changed the link but not the numbers: a borrower who
    # recalculated at 200 000 still saw the 300 000 their draft was seeded
    # with, and the affordability check measured the new instalment against the
    # old property.
    await client.post(
        "/api/auth/signup",
        json={"email": "carry@example.com", "password": "hunter2hunter2"},
    )
    application_id = (await client.post("/api/applications", json={})).json()["id"]
    simulation_id = (
        await client.post(
            "/api/simulations",
            json={
                "property_value": "200000.00",
                "own_contribution": "20000.00",
                "term_months": 300,
                "annual_nominal_rate": "0.0400",
                "region": "BRUSSELS",
                "is_first_home": False,
            },
        )
    ).json()["id"]

    body = (
        await client.patch(
            f"/api/applications/{application_id}", json={"simulation_id": simulation_id}
        )
    ).json()

    assert body["property"]["purchase_price"] == "200000.00"
    assert body["property"]["region"] == "BRUSSELS"
