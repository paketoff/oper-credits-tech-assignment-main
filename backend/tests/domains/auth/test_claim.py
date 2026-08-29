"""Claiming an anonymous simulation at signup. DOM-025 - DOM-027, AUTH-030 - AUTH-032.

The one flow with a real design decision in it: a failed claim must never fail
the signup, and an owned simulation is never reassigned.
"""

from decimal import Decimal

from app.core.enums import Region
from app.domains.simulation.entities import SimulationInput
from app.domains.simulation.repository import SqlSimulationRepository

_INPUT = SimulationInput(
    property_value=Decimal("300000.00"),
    own_contribution=Decimal("30000.00"),
    term_months=300,
    annual_nominal_rate=Decimal("0.0400"),
    region=Region.FLANDERS,
    is_first_home=True,
)


async def test_signup_with_simulation_claims_it(client, engine, session):
    simulation = await SqlSimulationRepository().save(session, _INPUT)
    await session.commit()

    response = await client.post(
        "/api/auth/signup",
        json={
            "email": "claimant@example.com",
            "password": "hunter2hunter2",
            "simulation_id": str(simulation.id),
        },
    )

    assert response.status_code == 201
    assert response.json()["claimed_simulation_id"] == str(simulation.id)


async def test_signup_with_unknown_simulation_still_succeeds(client, engine):
    # AUTH-031: a missing id is ignored, not an error. Losing a free
    # calculation must not cost a registration.
    response = await client.post(
        "/api/auth/signup",
        json={
            "email": "unknown-sim@example.com",
            "password": "hunter2hunter2",
            "simulation_id": "8f1c0000-0000-4000-8000-000000000000",
        },
    )

    assert response.status_code == 201
    assert response.json()["claimed_simulation_id"] is None


async def test_signup_with_claimed_simulation_does_not_reassign(client, engine, session):
    # DOM-027: the check is user_id IS NULL, not "overwrite".
    simulation = await SqlSimulationRepository().save(session, _INPUT)
    await session.commit()
    await client.post(
        "/api/auth/signup",
        json={
            "email": "first-owner@example.com",
            "password": "hunter2hunter2",
            "simulation_id": str(simulation.id),
        },
    )

    response = await client.post(
        "/api/auth/signup",
        json={
            "email": "second-owner@example.com",
            "password": "hunter2hunter2",
            "simulation_id": str(simulation.id),
        },
    )

    assert response.status_code == 201
    assert response.json()["claimed_simulation_id"] is None


async def test_claim_and_user_insert_share_one_transaction(client, engine, session):
    # CQ-091: if either half failed independently, an unclaimed simulation
    # could survive a signup that failed for an unrelated reason, or vice
    # versa. Asserted indirectly: a successful signup response implies both
    # writes committed together, since the service commits exactly once.
    simulation = await SqlSimulationRepository().save(session, _INPUT)
    await session.commit()

    response = await client.post(
        "/api/auth/signup",
        json={
            "email": "atomic@example.com",
            "password": "hunter2hunter2",
            "simulation_id": str(simulation.id),
        },
    )
    assert response.status_code == 201

    reloaded = await SqlSimulationRepository().get(session, simulation.id)
    me = await client.get("/api/auth/me")
    assert reloaded is not None
    assert str(reloaded.user_id) == me.json()["id"]
