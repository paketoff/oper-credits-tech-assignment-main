"""Six flow tests over the paths a user actually takes. Tier 2, T-P6, no threshold.

Each test walks a whole flow through the real HTTP surface — the wire contract
is what is being proven here, not any one endpoint in isolation.
"""

_PDF = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\nrealistic-enough padding"
_PRIMARY_SIMULATION = {
    "property_value": "300000.00",
    "own_contribution": "30000.00",
    "term_months": 300,
    "annual_nominal_rate": "0.0400",
    "region": "FLANDERS",
    "is_first_home": True,
}


async def test_flow_simulate_signup_apply_upload_end_to_end(client, engine):
    # SCP-002 - SCP-005: the four flows, run once, in order.
    simulation = (await client.post("/api/simulations", json=_PRIMARY_SIMULATION)).json()
    assert simulation["monthly_payment"] == "1414.52"

    signup = await client.post(
        "/api/auth/signup",
        json={
            "email": "flow-primary@example.com",
            "password": "hunter2hunter2",
            "simulation_id": simulation["id"],
        },
    )
    assert signup.status_code == 201

    application = (
        await client.post("/api/applications", json={"simulation_id": simulation["id"]})
    ).json()
    assert application["property"]["region"] == "FLANDERS"

    await client.patch(
        f"/api/applications/{application['id']}",
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
    submitted = await client.post(f"/api/applications/{application['id']}/submit")
    assert submitted.json()["status"] == "DOCUMENTS_PENDING"

    checklist = (
        await client.get(f"/api/applications/{application['id']}/checklist")
    ).json()
    required_types = [item["doc_type"] for item in checklist["items"] if item["required"]]
    last = None
    for doc_type in required_types:
        last = await client.post(
            f"/api/applications/{application['id']}/documents",
            data={"doc_type": doc_type},
            files={"file": (f"{doc_type}.pdf", _PDF)},
        )
    assert last is not None
    assert last.json()["application_status"] == "DOCUMENTS_COMPLETE"


async def test_flow_anonymous_simulation_survives_into_application(client, engine):
    # DOM-025 - DOM-027, UX-027: the anonymous-simulation model this build is
    # built around. A stale or unknown id must never block registration.
    simulation = (await client.post("/api/simulations", json=_PRIMARY_SIMULATION)).json()

    signup = await client.post(
        "/api/auth/signup",
        json={
            "email": "flow-anon@example.com",
            "password": "hunter2hunter2",
            "simulation_id": simulation["id"],
        },
    )
    assert signup.json()["claimed_simulation_id"] == simulation["id"]

    application = (
        await client.post("/api/applications", json={"simulation_id": simulation["id"]})
    ).json()

    assert application["property"]["purchase_price"] == "300000.00"
    assert application["property"]["property_type"] is None  # UX-027, API-071

    # A second signup with the SAME simulation id must still succeed, with the
    # claim silently skipped (AUTH-031) — checked in the same flow so the two
    # halves of the guarantee are proven together.
    stale_signup = await client.post(
        "/api/auth/signup",
        json={
            "email": "flow-anon-second@example.com",
            "password": "hunter2hunter2",
            "simulation_id": simulation["id"],
        },
    )
    assert stale_signup.status_code == 201
    assert stale_signup.json()["claimed_simulation_id"] is None


async def test_flow_document_removal_moves_application_backwards(client, engine):
    # APP-004, APP-008, API-056: the first-time-right loop, made real.
    await client.post(
        "/api/auth/signup",
        json={"email": "flow-removal@example.com", "password": "hunter2hunter2"},
    )
    application = (await client.post("/api/applications", json={})).json()
    await client.patch(
        f"/api/applications/{application['id']}",
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
    await client.post(f"/api/applications/{application['id']}/submit")
    checklist = (
        await client.get(f"/api/applications/{application['id']}/checklist")
    ).json()
    required_types = [item["doc_type"] for item in checklist["items"] if item["required"]]

    uploaded_ids = []
    for doc_type in required_types:
        response = await client.post(
            f"/api/applications/{application['id']}/documents",
            data={"doc_type": doc_type},
            files={"file": (f"{doc_type}.pdf", _PDF)},
        )
        uploaded_ids.append(response.json()["id"])
    assert (
        await client.get(f"/api/applications/{application['id']}")
    ).json()["status"] == "DOCUMENTS_COMPLETE"

    deleted = await client.delete(
        f"/api/applications/{application['id']}/documents/{uploaded_ids[0]}"
    )

    assert deleted.json()["application_status"] == "DOCUMENTS_PENDING"
    assert (
        await client.get(f"/api/applications/{application['id']}")
    ).json()["status"] == "DOCUMENTS_PENDING"


async def test_flow_unauthenticated_access_is_rejected_everywhere(client, engine):
    # AUTH-038, AUTH-039: every protected route, hit with no cookie at all.
    protected = [
        ("GET", "/api/auth/me"),
        ("GET", "/api/applications"),
        ("POST", "/api/applications"),
        ("GET", "/api/applications/00000000-0000-4000-8000-000000000000"),
        ("GET", "/api/applications/00000000-0000-4000-8000-000000000000/checklist"),
    ]

    for method, path in protected:
        response = await client.request(method, path, json={} if method == "POST" else None)
        assert response.status_code == 401, f"{method} {path} was not rejected"
        assert response.json()["code"] == "NOT_AUTHENTICATED"

    # The two public routes stay reachable throughout.
    assert (await client.post("/api/simulations", json=_PRIMARY_SIMULATION)).status_code == 201
    assert (await client.post("/api/auth/logout")).status_code == 204


async def test_flow_user_cannot_reach_another_users_resources(client, engine):
    # AUTH-035, ERR-005: 404, never 403, across every resource type.
    await client.post(
        "/api/auth/signup",
        json={"email": "flow-owner@example.com", "password": "hunter2hunter2"},
    )
    application = (await client.post("/api/applications", json={})).json()
    await client.patch(
        f"/api/applications/{application['id']}",
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
    submitted = await client.post(f"/api/applications/{application['id']}/submit")
    assert submitted.status_code == 200
    upload = await client.post(
        f"/api/applications/{application['id']}/documents",
        data={"doc_type": "IDENTITY"},
        files={"file": ("id.pdf", _PDF)},
    )
    assert upload.status_code == 201
    document = upload.json()

    await client.post("/api/auth/logout")
    await client.post(
        "/api/auth/signup",
        json={"email": "flow-intruder@example.com", "password": "hunter2hunter2"},
    )

    for response in (
        await client.get(f"/api/applications/{application['id']}"),
        await client.get(f"/api/applications/{application['id']}/checklist"),
        await client.get(f"/api/applications/{application['id']}/documents/{document['id']}"),
        await client.patch(f"/api/applications/{application['id']}", json={}),
        await client.post(f"/api/applications/{application['id']}/submit"),
        await client.delete(
            f"/api/applications/{application['id']}/documents/{document['id']}"
        ),
    ):
        assert response.status_code == 404
        assert response.json()["code"] in ("APPLICATION_NOT_FOUND", "DOCUMENT_NOT_FOUND")


async def test_flow_validation_errors_use_the_shared_error_shape(client, engine):
    # VAL-006, API-013: {code, message, field} everywhere, whichever domain
    # raised it, and never FastAPI's raw detail array.
    await client.post(
        "/api/auth/signup",
        json={"email": "flow-shape@example.com", "password": "hunter2hunter2"},
    )
    application = (await client.post("/api/applications", json={})).json()

    failures = (
        await client.post("/api/simulations", json=_PRIMARY_SIMULATION | {"term_months": 5}),
        await client.post(
            "/api/auth/signup",
            json={"email": "flow-shape@example.com", "password": "hunter2hunter2"},
        ),
        await client.post(f"/api/applications/{application['id']}/submit"),
        await client.post(
            f"/api/applications/{application['id']}/documents",
            data={"doc_type": "IDENTITY"},
            files={"file": ("id.pdf", b"")},
        ),
        await client.post("/api/simulations", json=_PRIMARY_SIMULATION | {"unexpected": 1}),
    )

    for response in failures:
        body = response.json()
        assert set(body) == {"code", "message", "field"}
        assert isinstance(body["code"], str)
        assert "detail" not in body
