"""Five tables, and repositories that return entities rather than rows.

CQ-085 - CQ-092. The ORM boundary is the thing being tested here: if a
`SimulationRow` ever reaches a service, a lazy load will eventually fire against
a closed session and the failure will surface a long way from this file.
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
from app.core.enums import DocumentType, Region
from app.domains.applications.entities import (
    Borrower,
    EmploymentType,
)
from app.domains.applications.repository import SqlApplicationRepository
from app.domains.auth.repository import SqlUserRepository
from app.domains.documents.entities import Document
from app.domains.documents.repository import SqlDocumentRepository
from app.domains.simulation.entities import Simulation, SimulationInput
from app.domains.simulation.repository import SqlSimulationRepository
from app.domains.simulation.tables import SimulationRow

_INPUT = SimulationInput(
    property_value=Decimal("300000.00"),
    own_contribution=Decimal("30000.00"),
    term_months=300,
    annual_nominal_rate=Decimal("0.0400"),
    region=Region.FLANDERS,
    is_first_home=True,
)


async def test_create_all_builds_every_table(engine):
    # CQ-085: six tables, no more and no fewer. `application_financials` is a
    # table of its own rather than columns on `borrowers` because API-037
    # replaces that collection wholesale on every PATCH (DOM-029).
    expected = {
        "users",
        "simulations",
        "applications",
        "borrowers",
        "documents",
        "application_financials",
    }
    async with engine.connect() as connection:
        names = await connection.run_sync(lambda sync: set(inspect(sync).get_table_names()))

    assert expected <= names
    assert set(Base.metadata.tables) == expected


async def test_users_email_unique_index_exists(session):
    # CQ-092, AUTH-022. The check in the service gives a clean message; this
    # constraint is what makes it correct when two signups race.
    users = SqlUserRepository()
    await users.create(session, "race@example.com", "hash")

    with pytest.raises(IntegrityError):
        await users.create(session, "race@example.com", "other-hash")


async def test_users_email_is_unique_case_insensitively(session):
    # VAL-020: signing up as Test@Example.com when test@example.com exists.
    # Normalising in Python alone would leave the database willing to store
    # both, so the column collates NOCASE.
    users = SqlUserRepository()
    await users.create(session, "jan@example.com", "hash")

    with pytest.raises(IntegrityError):
        await users.create(session, "JAN@example.com", "hash")


async def test_repository_returns_domain_model_not_orm_row(session):
    # CQ-088. The whole point of the boundary.
    simulations = SqlSimulationRepository()

    saved = await simulations.save(session, _INPUT)

    assert isinstance(saved, Simulation)
    assert not isinstance(saved, SimulationRow)
    assert saved.request.region is Region.FLANDERS


async def test_money_columns_load_as_decimal(session):
    # CQ-086, DOM-003. A float here loses cents, and the build is judged on
    # cents. Round-tripped rather than asserted on the object we just built.
    simulations = SqlSimulationRepository()
    saved = await simulations.save(session, _INPUT)

    reloaded = await simulations.get(session, saved.id)

    assert reloaded is not None
    assert isinstance(reloaded.request.property_value, Decimal)
    assert not isinstance(reloaded.request.property_value, float)
    assert reloaded.request.property_value == Decimal("300000.00")
    assert reloaded.request.annual_nominal_rate == Decimal("0.0400")


async def test_set_owner_only_claims_an_unowned_simulation(session):
    # DOM-027. The condition is in the WHERE clause, so two concurrent claims
    # cannot both succeed.
    # Real users, not invented uuids: the foreign key is on and would reject
    # them — which is itself a check that the T13 pragma is doing its job.
    simulations = SqlSimulationRepository()
    users = SqlUserRepository()
    saved = await simulations.save(session, _INPUT)
    first = await users.create(session, "first@example.com", "hash")
    second = await users.create(session, "second@example.com", "hash")

    claimed = await simulations.set_owner(session, saved.id, first.id)
    stolen = await simulations.set_owner(session, saved.id, second.id)

    assert claimed is not None
    assert claimed.user_id == first.id
    assert stolen is None


async def test_application_borrowers_are_eagerly_loaded(session):
    # CQ-089. If this returned an unloaded collection the assertion would raise
    # rather than fail, which is the behaviour the rule exists to prevent.
    users = SqlUserRepository()
    applications = SqlApplicationRepository()
    user = await users.create(session, "owner@example.com", "hash")
    application = await applications.create(session, user.id, None, None)

    await applications.replace_borrowers(
        session,
        application.id,
        (
            Borrower(
                full_name="Jan Test",
                date_of_birth=date(1990, 4, 12),
                employment_type=EmploymentType.EMPLOYEE,
                monthly_net_income=Decimal("3200.00"),
                has_existing_credit=False,
            ),
        ),
    )
    reloaded = await applications.get(session, application.id)

    assert reloaded is not None
    assert reloaded.borrowers[0].full_name == "Jan Test"
    assert reloaded.borrowers[0].employment_type is EmploymentType.EMPLOYEE


async def test_replacing_borrowers_is_wholesale(session):
    # API-037. Two calls, and the second wins entirely.
    users = SqlUserRepository()
    applications = SqlApplicationRepository()
    user = await users.create(session, "wholesale@example.com", "hash")
    application = await applications.create(session, user.id, None, None)

    def _borrower(name: str) -> Borrower:
        return Borrower(
            full_name=name,
            date_of_birth=date(1990, 4, 12),
            employment_type=EmploymentType.EMPLOYEE,
            monthly_net_income=None,
            has_existing_credit=False,
        )

    await applications.replace_borrowers(session, application.id, (_borrower("First"),))
    await applications.replace_borrowers(session, application.id, (_borrower("Second"),))
    reloaded = await applications.get(session, application.id)

    assert reloaded is not None
    assert [b.full_name for b in reloaded.borrowers] == ["Second"]


async def test_a_draft_can_be_seeded_from_a_simulation(session):
    # API-032, ARC-047: region, first-home status and price arrive already
    # filled — what stops the borrower being asked twice (UX-002). property_type
    # is deliberately absent: a simulation never asks existing-vs-new-build, so
    # the section stays incomplete (property_details is None) until the
    # borrower answers that in the wizard.
    from app.domains.applications.entities import PropertySeed

    users = SqlUserRepository()
    applications = SqlApplicationRepository()
    user = await users.create(session, "seeded@example.com", "hash")
    seed = PropertySeed(
        region=Region.FLANDERS,
        is_first_home=True,
        purchase_price=Decimal("300000.00"),
    )

    application = await applications.create(session, user.id, seed, None)

    # property_details stays None (property_type is unknown), but property_seed
    # carries what a simulation actually can prefill (UX-027).
    assert application.property_details is None
    assert application.property_seed == seed


async def test_documents_round_trip_and_list_by_application(session):
    users = SqlUserRepository()
    applications = SqlApplicationRepository()
    documents = SqlDocumentRepository()
    user = await users.create(session, "docs@example.com", "hash")
    application = await applications.create(session, user.id, None, None)
    document = Document(
        id=uuid4(),
        application_id=application.id,
        doc_type=DocumentType.PAYSLIPS,
        filename="loonfiche-maart.pdf",
        storage_key=f"{application.id}/{uuid4()}",
        content_type="application/pdf",
        size_bytes=184320,
        uploaded_at=None,  # type: ignore[arg-type]  # the column defaults it
    )

    await documents.create(session, document)
    listed = await documents.list_for_application(session, application.id)

    assert [d.doc_type for d in listed] == [DocumentType.PAYSLIPS]
    assert listed[0].filename == "loonfiche-maart.pdf"
