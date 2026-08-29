"""The simulation wire contract. API-018 - API-022, and AC-003 to the cent."""

import pytest

_PRIMARY = {
    "property_value": "300000.00",
    "own_contribution": "30000.00",
    "term_months": 300,
    "annual_nominal_rate": "0.0400",
    "region": "FLANDERS",
    "is_first_home": True,
}


async def test_create_simulation_returns_primary_case_body(client, engine):
    response = await client.post("/api/simulations", json=_PRIMARY)

    assert response.status_code == 201
    body = response.json()
    assert body["loan_amount"] == "270000.00"
    assert body["quotiteit"] == "0.9000"
    assert body["above_supervisory_norm"] is False
    assert body["monthly_payment"] == "1414.52"
    assert body["total_paid"] == "424356.04"
    assert body["total_interest"] == "154356.04"
    assert body["upfront"]["registration_duty"] == "6000.00"
    assert body["upfront"]["total_cash_needed"] == "43175.00"
    assert body["jkp"].startswith("0.0414")


async def test_create_simulation_persists_and_is_retrievable(client, engine):
    created = (await client.post("/api/simulations", json=_PRIMARY)).json()

    fetched = await client.get(f"/api/simulations/{created['id']}")

    assert fetched.status_code == 200
    assert fetched.json()["monthly_payment"] == created["monthly_payment"]
    assert fetched.json()["id"] == created["id"]


async def test_money_fields_serialise_as_strings(client, engine):
    # API-004, API-064, CQ-014. Asserted on the raw body rather than on a
    # parsed model: a float here would still compare equal after parsing, and
    # the cent would go missing on the other side of the wire.
    import json

    raw = json.loads((await client.post("/api/simulations", json=_PRIMARY)).text)
    money = [
        raw["loan_amount"],
        raw["monthly_payment"],
        raw["total_paid"],
        raw["quotiteit"],
        raw["nominal_rate"],
        raw["jkp"],
        *raw["upfront"].values(),
    ]

    assert all(isinstance(value, str) for value in money)
    assert not any(isinstance(value, float) for value in money)


async def test_rates_and_ratios_carry_four_decimals(client, engine):
    # API-005, API-006, VAL-019. "0.04" would be a valid Decimal and the wrong
    # contract; the frontend should never have to normalise what it is given.
    body = (await client.post("/api/simulations", json=_PRIMARY)).json()

    assert body["nominal_rate"] == "0.0400"
    assert body["quotiteit"] == "0.9000"


async def test_own_contribution_equal_to_price_returns_422(client, engine):
    payload = _PRIMARY | {"own_contribution": "300000.00"}

    response = await client.post("/api/simulations", json=payload)

    assert response.status_code == 422
    assert response.json()["code"] == "LOAN_AMOUNT_NOT_POSITIVE"
    assert response.json()["field"] == "own_contribution"


@pytest.mark.parametrize("term", [11, 361])
async def test_term_out_of_range_returns_422(client, engine, term):
    response = await client.post("/api/simulations", json=_PRIMARY | {"term_months": term})

    assert response.status_code == 422
    assert response.json()["code"] == "TERM_OUT_OF_RANGE"


async def test_rate_above_the_ceiling_returns_its_own_code(client, engine):
    response = await client.post(
        "/api/simulations", json=_PRIMARY | {"annual_nominal_rate": "0.2001"}
    )

    assert response.json()["code"] == "RATE_OUT_OF_RANGE"


async def test_property_value_out_of_range_returns_its_own_code(client, engine):
    response = await client.post("/api/simulations", json=_PRIMARY | {"property_value": "9999.00"})

    assert response.json()["code"] == "PROPERTY_VALUE_OUT_OF_RANGE"


async def test_extra_field_is_rejected(client, engine):
    # CQ-025, VAL-020: extra="forbid". An unexpected field is an error, not
    # something silently dropped.
    response = await client.post("/api/simulations", json=_PRIMARY | {"surprise": 1})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


async def test_unknown_simulation_returns_404(client, engine):
    response = await client.get("/api/simulations/8f1c0000-0000-4000-8000-000000000000")

    assert response.status_code == 404
    assert response.json()["code"] == "SIMULATION_NOT_FOUND"


async def test_zero_own_contribution_is_valid_and_flagged(client, engine):
    # AC-007, VAL-009: quotiteit 100% is valid. Belgium has no statutory LTV
    # cap, and rejecting it would be a domain error on our side.
    body = (await client.post("/api/simulations", json=_PRIMARY | {"own_contribution": "0"})).json()

    assert body["quotiteit"] == "1.0000"
    assert body["above_supervisory_norm"] is True
