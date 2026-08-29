"""Queries against the applications and borrowers tables."""

from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import Region
from app.domains.applications.entities import (
    Application,
    ApplicationStatus,
    Borrower,
    EmploymentType,
    PropertyDetails,
    PropertySeed,
    PropertyType,
)
from app.domains.applications.tables import ApplicationRow, BorrowerRow


class ApplicationRepository(Protocol):
    """Persistence for applications and their borrowers."""

    async def create(
        self,
        session: AsyncSession,
        user_id: UUID,
        seed: PropertySeed | None,
        simulation_id: UUID | None,
    ) -> Application:
        """Insert a draft application, optionally seeded from a simulation."""
        ...

    async def get(self, session: AsyncSession, application_id: UUID) -> Application | None:
        """Fetch one application with its borrowers loaded, or None."""
        ...

    async def list_for_user(self, session: AsyncSession, user_id: UUID) -> list[Application]:
        """Every application this user owns, newest last."""
        ...

    async def replace_borrowers(
        self, session: AsyncSession, application_id: UUID, borrowers: tuple[Borrower, ...]
    ) -> None:
        """Replace the borrower collection wholesale (API-037)."""
        ...

    async def update(
        self,
        session: AsyncSession,
        application_id: UUID,
        property_details: PropertyDetails | None,
        status: ApplicationStatus | None,
    ) -> Application | None:
        """Apply a partial update and return the reloaded application."""
        ...


def _to_borrower(row: BorrowerRow) -> Borrower:
    """Map a borrower row to the domain type."""
    return Borrower(
        id=row.id,
        full_name=row.full_name,
        date_of_birth=row.date_of_birth,
        employment_type=EmploymentType(row.employment_type),
        monthly_net_income=row.monthly_net_income,
        has_existing_credit=row.has_existing_credit,
    )


def _to_property_details(row: ApplicationRow) -> PropertyDetails | None:
    """Assemble the *complete* property section, or None if it is not yet whole.

    Requires all four columns, `property_type` included — this is the
    checklist-ready view `ApplicationProfile` depends on (DOC-005).
    """
    if row.region is None or row.property_type is None or row.purchase_price is None:
        return None
    return PropertyDetails(
        region=Region(row.region),
        is_first_home=bool(row.is_first_home),
        property_type=PropertyType(row.property_type),
        purchase_price=row.purchase_price,
    )


def _to_property_seed(row: ApplicationRow) -> PropertySeed | None:
    """Assemble whatever is known about the property, `property_type` aside.

    Present as soon as a simulation seeds a draft (API-032), even though the
    complete, checklist-ready section is not — a simulation never asks
    existing-vs-new-build, so this is what lets the wizard show a prefilled
    price and region while still asking that one question (UX-027).
    """
    if row.region is None or row.purchase_price is None:
        return None
    return PropertySeed(
        region=Region(row.region),
        is_first_home=bool(row.is_first_home),
        purchase_price=row.purchase_price,
    )


def _to_entity(row: ApplicationRow) -> Application:
    """Map a row and its loaded borrowers to the domain type."""
    return Application(
        id=row.id,
        user_id=row.user_id,
        simulation_id=row.simulation_id,
        status=ApplicationStatus(row.status),
        borrowers=tuple(_to_borrower(borrower) for borrower in row.borrowers),
        property_details=_to_property_details(row),
        property_seed=_to_property_seed(row),
        submitted_at=row.submitted_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlApplicationRepository:
    """The SQLite implementation of `ApplicationRepository`.

    Every read uses `selectinload` for the borrowers. A lazy load would fire
    outside this module, against a session the request has already closed —
    the classic source of mysterious errors CQ-089 exists to prevent.
    """

    async def create(
        self,
        session: AsyncSession,
        user_id: UUID,
        seed: PropertySeed | None,
        simulation_id: UUID | None,
    ) -> Application:
        """Insert a draft, carrying over what the simulation already told us.

        `property_type` is never seeded: a simulation does not ask for it, so
        the column stays null and the property section stays incomplete until
        the borrower answers that question in the wizard.
        """
        row = ApplicationRow(
            user_id=user_id,
            simulation_id=simulation_id,
            status=ApplicationStatus.DRAFT.value,
            region=seed.region.value if seed else None,
            is_first_home=seed.is_first_home if seed else None,
            property_type=None,
            purchase_price=seed.purchase_price if seed else None,
        )
        session.add(row)
        await session.flush()
        return await self._reload(session, row.id)

    async def get(self, session: AsyncSession, application_id: UUID) -> Application | None:
        """Fetch one application with its borrowers."""
        statement = (
            select(ApplicationRow)
            .where(ApplicationRow.id == application_id)
            .options(selectinload(ApplicationRow.borrowers))
        )
        row = (await session.execute(statement)).scalar_one_or_none()
        return _to_entity(row) if row else None

    async def list_for_user(self, session: AsyncSession, user_id: UUID) -> list[Application]:
        """Every application this user owns."""
        statement = (
            select(ApplicationRow)
            .where(ApplicationRow.user_id == user_id)
            .options(selectinload(ApplicationRow.borrowers))
            .order_by(ApplicationRow.created_at)
        )
        rows = (await session.execute(statement)).scalars().all()
        return [_to_entity(row) for row in rows]

    async def replace_borrowers(
        self, session: AsyncSession, application_id: UUID, borrowers: tuple[Borrower, ...]
    ) -> None:
        """Swap the whole collection.

        Wholesale rather than element by element (API-037): a partial merge of
        an unordered collection has no unambiguous meaning, and the wizard sends
        the full set every time anyway.
        """
        statement = (
            select(ApplicationRow)
            .where(ApplicationRow.id == application_id)
            .options(selectinload(ApplicationRow.borrowers))
        )
        row = (await session.execute(statement)).scalar_one()
        row.borrowers.clear()
        for borrower in borrowers:
            row.borrowers.append(
                BorrowerRow(
                    full_name=borrower.full_name,
                    date_of_birth=borrower.date_of_birth,
                    employment_type=borrower.employment_type.value,
                    monthly_net_income=borrower.monthly_net_income,
                    has_existing_credit=borrower.has_existing_credit,
                )
            )
        await session.flush()

    async def update(
        self,
        session: AsyncSession,
        application_id: UUID,
        property_details: PropertyDetails | None,
        status: ApplicationStatus | None,
    ) -> Application | None:
        """Apply whichever of the two sections was supplied."""
        row = await session.get(ApplicationRow, application_id)
        if row is None:
            return None
        if property_details is not None:
            row.region = property_details.region.value
            row.is_first_home = property_details.is_first_home
            row.property_type = property_details.property_type.value
            row.purchase_price = property_details.purchase_price
        if status is not None:
            row.status = status.value
        await session.flush()
        return await self._reload(session, application_id)

    async def _reload(self, session: AsyncSession, application_id: UUID) -> Application:
        """Read the row back with its borrowers, so no caller lazy-loads."""
        loaded = await self.get(session, application_id)
        if loaded is None:  # pragma: no cover - the row was just written
            raise LookupError(application_id)
        return loaded
