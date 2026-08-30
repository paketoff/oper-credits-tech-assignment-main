"""Application flow: draft, patch, submit, recompute status."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import DocumentType
from app.core.errors import ApplicationError, NotFoundError
from app.domains.applications import affordability, state_machine
from app.domains.applications.checklist import mark_satisfied, required_documents
from app.domains.applications.entities import (
    AffordabilityInput,
    Application,
    ApplicationStatus,
    Borrower,
    ConfirmedAmount,
    DocumentRequirement,
    FinancialProfile,
    PropertyDetails,
    PropertySeed,
    PropertyType,
    Provenance,
)
from app.domains.applications.repository import ApplicationRepository
from app.domains.applications.schemas import (
    AffordabilityResponse,
    ApplicationCreateRequest,
    ApplicationListResponse,
    ApplicationPatchRequest,
    ApplicationResponse,
    ApplicationSummary,
    BorrowerRequest,
    BorrowerResponse,
    ConfirmedAmountResponse,
    FinancialsRequest,
    FinancialsResponse,
    PropertyRequest,
    PropertyResponse,
)
from app.domains.simulation.entities import Simulation
from app.domains.simulation.service import SimulationService

# APP-010, SCP-018. UNDER_REVIEW and beyond is where a person, not the
# borrower, is looking at the file — so a PATCH stops being safe there.
# DOCUMENTS_PENDING and DOCUMENTS_COMPLETE stay writable on purpose: VAL-020
# requires editing employment_type after documents already exist to upload,
# which is only possible past DRAFT (API-040, narrowed at T21).
_LOCKED_FOR_EDITING = frozenset(
    {ApplicationStatus.UNDER_REVIEW, ApplicationStatus.OFFER_ISSUED, ApplicationStatus.WITHDRAWN}
)

# VAL-011, DOM-028.
_MIN_AGE = 18
_MAX_AGE = 75


class ApplicationService:
    """Creates, reads and updates applications."""

    def __init__(self, repository: ApplicationRepository, simulations: SimulationService) -> None:
        """Take the repository as a protocol, and the one foreign service (ARC-047)."""
        self._repository = repository
        self._simulations = simulations

    async def create(
        self, session: AsyncSession, user_id: UUID, payload: ApplicationCreateRequest
    ) -> ApplicationResponse:
        """Create a draft, seeded from a simulation when one is given (API-032).

        This is the normal path after signup, not a fallback: signup only
        claims a simulation (`2-architecture.md` §5.1), and this is where the
        draft it seeds actually gets created.
        """
        seed = await self._seed_from_simulation(session, user_id, payload.simulation_id)
        simulation_id = payload.simulation_id if seed is not None else None
        application = await self._repository.create(session, user_id, seed, simulation_id)
        await session.commit()
        return self._to_response(application, frozenset())

    async def list_for_user(
        self,
        session: AsyncSession,
        user_id: UUID,
        uploaded_by_application: dict[UUID, frozenset[DocumentType]],
    ) -> ApplicationListResponse:
        """The summary list: only this user's applications (API-029, AUTH-034)."""
        applications = await self._repository.list_for_user(session, user_id)
        items = [
            self._to_summary(app, uploaded_by_application.get(app.id, frozenset()))
            for app in applications
        ]
        return ApplicationListResponse(items=items)

    async def ids_for_user(self, session: AsyncSession, user_id: UUID) -> list[UUID]:
        """Just the ids this user owns, for a caller that needs them first.

        `documents.service` needs to know *which* applications to count
        documents for before it can hand `list_for_user` the map it takes, and
        it may not query the applications table itself (ARC-009).
        """
        return [app.id for app in await self._repository.list_for_user(session, user_id)]

    async def get(
        self, session: AsyncSession, application_id: UUID, user_id: UUID
    ) -> ApplicationResponse:
        """Fetch one application, scoped to its owner (API-033, API-034)."""
        application = await self.get_owned(session, application_id, user_id)
        return self._to_response(application, frozenset())

    async def patch(
        self,
        session: AsyncSession,
        application_id: UUID,
        user_id: UUID,
        payload: ApplicationPatchRequest,
    ) -> ApplicationResponse:
        """Apply a partial update (API-035 - API-039).

        Only the keys present in `payload` are touched (API-036): draft steps
        the borrower has not reached yet must not be pre-validated (UX-032).

        Raises:
            ApplicationError: APPLICATION_ALREADY_SUBMITTED once the
                application has left the document-collection phase.
        """
        application = await self.get_owned(session, application_id, user_id)
        if application.status in _LOCKED_FOR_EDITING:
            raise ApplicationError(code="APPLICATION_ALREADY_SUBMITTED")

        if payload.borrowers is not None:
            borrowers = tuple(self._to_borrower(b) for b in payload.borrowers)
            await self._repository.replace_borrowers(session, application_id, borrowers)
        attached = (
            await self._attach_simulation(session, application_id, user_id, payload.simulation_id)
            if payload.simulation_id is not None
            else None
        )
        property_details = self._to_property(payload.property) if payload.property else None
        # Attaching a simulation carries its figures onto the application.
        # Without this the link changed but the price did not: a borrower who
        # recalculated at 200 000 still saw the 300 000 their draft was seeded
        # with, and the affordability check measured the new instalment against
        # the old property.
        if attached is not None and property_details is None:
            property_details = self._property_from(attached, application)
        updated = await self._repository.update(session, application_id, property_details, None)
        if updated is None:
            raise NotFoundError(code="APPLICATION_NOT_FOUND")
        await session.commit()
        return self._to_response(updated, frozenset())

    async def submit(
        self, session: AsyncSession, application_id: UUID, user_id: UUID
    ) -> ApplicationResponse:
        """Validate everything and transition DRAFT -> SUBMITTED -> DOCUMENTS_PENDING.

        The move to `DOCUMENTS_PENDING` is automatic (APP-002): a borrower never
        sees `SUBMITTED` sit still, because there is nothing to do in that state
        before the checklist takes over.

        Raises:
            ApplicationError: VALIDATION_ERROR naming the first missing field
                (API-042); APPLICATION_ALREADY_SUBMITTED on a second call
                (API-043); INVALID_STATE_TRANSITION from any other state, i.e.
                WITHDRAWN (API-044).
        """
        application = await self.get_owned(session, application_id, user_id)
        self._validate_for_submission(application)
        self._assert_submittable(application.status)
        state_machine.assert_transition(application.status, ApplicationStatus.SUBMITTED)
        state_machine.assert_transition(
            ApplicationStatus.SUBMITTED, ApplicationStatus.DOCUMENTS_PENDING
        )
        updated = await self._repository.update(
            session, application_id, None, ApplicationStatus.DOCUMENTS_PENDING
        )
        if updated is None:
            raise NotFoundError(code="APPLICATION_NOT_FOUND")
        await session.commit()
        return self._to_response(updated, frozenset())

    async def recompute_status(
        self,
        session: AsyncSession,
        application_id: UUID,
        uploaded: frozenset[DocumentType],
    ) -> ApplicationStatus:
        """Move between DOCUMENTS_PENDING and DOCUMENTS_COMPLETE (APP-003, APP-004).

        Called from `documents.service` (ARC-018) after an upload or a
        deletion. `uploaded` is passed in rather than fetched, because only
        `documents` may query the documents table (ARC-009) — the arrow points
        one way, and this keeps it pointing that way.
        """
        application = await self._repository.get(session, application_id)
        if application is None:
            raise NotFoundError(code="APPLICATION_NOT_FOUND")
        if application.status not in (
            ApplicationStatus.DOCUMENTS_PENDING,
            ApplicationStatus.DOCUMENTS_COMPLETE,
        ):
            return application.status

        target = (
            ApplicationStatus.DOCUMENTS_COMPLETE
            if self._all_satisfied(application, uploaded)
            else ApplicationStatus.DOCUMENTS_PENDING
        )
        if target == application.status:
            return application.status
        state_machine.assert_transition(application.status, target)
        updated = await self._repository.update(session, application_id, None, target)
        if updated is None:
            raise NotFoundError(code="APPLICATION_NOT_FOUND")
        return updated.status

    async def get_financials(
        self, session: AsyncSession, application_id: UUID, user_id: UUID
    ) -> FinancialsResponse:
        """The confirmed profile and the assessment derived from it (API-074)."""
        application = await self.get_owned(session, application_id, user_id)
        profile = await self._repository.get_financials(session, application_id)
        return await self._to_financials_response(session, application, profile)

    async def put_financials(
        self,
        session: AsyncSession,
        application_id: UUID,
        user_id: UUID,
        payload: FinancialsRequest,
    ) -> FinancialsResponse:
        """Replace the confirmed profile wholesale (API-073).

        Every figure written here is `MANUAL`, including one the borrower
        accepted from a document's proposal: accepting fills the form, and the
        borrower still presses save, so what arrives here is what they
        submitted (DOM-030). `Provenance.DOCUMENT` therefore has no live path
        in this build — deliberately. Writing it would mean trusting the client
        to assert its own provenance, and verifying the claim instead would
        need `applications` to read the documents table, which ARC-009 forbids.
        Recorded in `docs/sessions/p4-review.md` rather than left to be noticed.
        """
        application = await self.get_owned(session, application_id, user_id)
        confirmed_at = datetime.now(UTC)
        profile = FinancialProfile(
            application_id=application_id,
            net_monthly_income=self._manual(payload.net_monthly_income, confirmed_at),
            existing_credit_monthly=self._manual(payload.existing_credit_monthly, confirmed_at),
            dependants=payload.dependants,
            updated_at=confirmed_at,
        )
        saved = await self._repository.upsert_financials(session, profile)
        await session.commit()
        return await self._to_financials_response(session, application, saved)

    def _manual(self, amount: Decimal | None, confirmed_at: datetime) -> ConfirmedAmount | None:
        """Wrap a typed figure with its provenance, or keep it absent."""
        if amount is None:
            return None
        return ConfirmedAmount(
            amount=amount,
            provenance=Provenance.MANUAL,
            source_document_id=None,
            confirmed_at=confirmed_at,
        )

    async def _to_financials_response(
        self,
        session: AsyncSession,
        application: Application,
        profile: FinancialProfile | None,
    ) -> FinancialsResponse:
        """Assemble the body, running the assessment when there is a loan to measure."""
        assessment = await self._assess(session, application, profile)
        return FinancialsResponse(
            net_monthly_income=_to_amount_response(
                profile.net_monthly_income if profile else None
            ),
            existing_credit_monthly=_to_amount_response(
                profile.existing_credit_monthly if profile else None
            ),
            dependants=profile.dependants if profile else 0,
            assessment=assessment,
            updated_at=profile.updated_at if profile else None,
        )

    async def _assess(
        self,
        session: AsyncSession,
        application: Application,
        profile: FinancialProfile | None,
    ) -> AffordabilityResponse | None:
        """Run the affordability assessment, or None when there is nothing to measure.

        The monthly payment comes from the linked simulation through the ARC-047
        edge. Without one there is no instalment, and an assessment against an
        invented figure would be worse than none at all.
        """
        if application.simulation_id is None:
            return None
        payment = await self._simulations.monthly_payment_for(session, application.simulation_id)
        if payment is None:
            return None
        result = affordability.assess(
            AffordabilityInput(
                net_monthly_income=profile.net_monthly_income.amount
                if profile and profile.net_monthly_income
                else None,
                existing_credit_monthly=profile.existing_credit_monthly.amount
                if profile and profile.existing_credit_monthly
                else None,
                dependants=profile.dependants if profile else 0,
                adults=max(1, len(application.borrowers)),
            ),
            payment,
        )
        return AffordabilityResponse(
            band=result.band,
            dsti=result.dsti,
            monthly_obligations=result.monthly_obligations,
            residual_income=result.residual_income,
            residual_floor=result.residual_floor,
        )

    def checklist(
        self, application: Application, uploaded: frozenset[DocumentType]
    ) -> list[DocumentRequirement]:
        """Derive and mark the checklist for one application (DOC-005 - DOC-011).

        Takes `uploaded` as an argument rather than querying for it, for the
        same reason `recompute_status` does: `applications` may not touch the
        documents table.
        """
        requirements = required_documents(application.profile())
        return mark_satisfied(requirements, uploaded)

    async def _attach_simulation(
        self, session: AsyncSession, application_id: UUID, user_id: UUID, simulation_id: UUID
    ) -> Simulation:
        """Point the application at a simulation this borrower may have.

        Three cases, and the middle one is the ordinary path: `POST
        /api/simulations` is public and sets no owner (DOM-025), so a borrower
        who runs the calculator while already signed in produces an *anonymous*
        simulation. Claiming it here is the same move signup makes, through the
        same method — an unowned calculation belongs to whoever holds its
        unguessable id (DOM-027).

        Resolved through `simulation.service`, never its repository (ARC-047).

        Raises:
            NotFoundError: SIMULATION_NOT_FOUND when it does not exist, or
                belongs to somebody else. Unlike seeding at creation — where a
                missing simulation must not block making an application
                (AUTH-031) — this was asked for explicitly, so failing silently
                would leave the borrower pressing a button that does nothing.
        """
        simulation = await self._simulations.get_stored(session, simulation_id)
        if simulation is None:
            raise NotFoundError(code="SIMULATION_NOT_FOUND")

        if simulation.user_id is None:
            # The claim carries the `user_id IS NULL` condition in its own
            # WHERE, so two borrowers racing for the same id cannot both win.
            if await self._simulations.claim_for_user(session, simulation_id, user_id) is None:
                raise NotFoundError(code="SIMULATION_NOT_FOUND")
        elif simulation.user_id != user_id:
            raise NotFoundError(code="SIMULATION_NOT_FOUND")
        await self._repository.attach_simulation(session, application_id, simulation_id)
        return simulation

    def _property_from(self, simulation: Simulation, application: Application) -> PropertyDetails:
        """The property section as the newly attached simulation states it.

        `property_type` is not something a simulation asks, so whatever the
        borrower already answered is kept (`EXISTING` for a draft that never
        reached that step).
        """
        existing = application.property_details
        return PropertyDetails(
            region=simulation.request.region,
            is_first_home=simulation.request.is_first_home,
            property_type=existing.property_type if existing else PropertyType.EXISTING,
            purchase_price=simulation.request.property_value,
        )

    async def _seed_from_simulation(
        self, session: AsyncSession, user_id: UUID, simulation_id: UUID | None
    ) -> PropertySeed | None:
        """Read a simulation this user owns and turn it into a seed.

        The cross-domain edge ARC-047: reading through `simulation.service`
        rather than its repository (ARC-011). A simulation that does not exist
        or belongs to someone else seeds nothing — a missing seed must not
        block creating a blank application, the same reasoning as AUTH-031.
        """
        if simulation_id is None:
            return None
        simulation = await self._simulations.get_stored(session, simulation_id)
        if simulation is None or simulation.user_id != user_id:
            return None
        return PropertySeed(
            region=simulation.request.region,
            is_first_home=simulation.request.is_first_home,
            purchase_price=simulation.request.property_value,
        )

    async def get_owned(
        self, session: AsyncSession, application_id: UUID, user_id: UUID
    ) -> Application:
        """Fetch an application owned by this user.

        Public: this is the cross-domain edge `2-architecture.md` ARC-018
        widened past `recompute_status` — `documents.service` calls it to
        resolve the application before deriving a checklist, since only
        `applications` may build an `ApplicationProfile` (ARC-009 keeps the
        documents table off limits to it).

        Raises:
            NotFoundError: APPLICATION_NOT_FOUND for both "does not exist" and
                "belongs to someone else" — the two are indistinguishable from
                the outside, by design (AUTH-035, ERR-005).
        """
        application = await self._repository.get(session, application_id)
        if application is None or application.user_id != user_id:
            raise NotFoundError(code="APPLICATION_NOT_FOUND")
        return application

    def _assert_submittable(self, status: ApplicationStatus) -> None:
        """Distinguish "already submitted" from "cannot ever be submitted".

        The bare state machine cannot tell these apart: both are simply not
        `DRAFT`. API-043 wants a second submit to answer with a specific,
        friendly conflict code; API-044 reserves INVALID_STATE_TRANSITION for
        the state that was never reachable from submission in the first place.

        Raises:
            ApplicationError: APPLICATION_ALREADY_SUBMITTED once the file has
                already gone through submit; INVALID_STATE_TRANSITION from
                WITHDRAWN, the one state submission was never the path to.
        """
        if status == ApplicationStatus.DRAFT:
            return
        if status == ApplicationStatus.WITHDRAWN:
            raise ApplicationError(code="INVALID_STATE_TRANSITION")
        raise ApplicationError(code="APPLICATION_ALREADY_SUBMITTED")

    def _validate_for_submission(self, application: Application) -> None:
        """Full validation across every step, run once at submit (VAL-012).

        Raises:
            ApplicationError: VALIDATION_ERROR, naming the first missing field
                so the frontend can point at it (API-042).
        """
        if not application.borrowers:
            raise ApplicationError(code="VALIDATION_ERROR", field="borrowers")
        if application.property_details is None:
            raise ApplicationError(code="VALIDATION_ERROR", field="property")
        for borrower in application.borrowers:
            if not _MIN_AGE <= _age_at(borrower.date_of_birth) <= _MAX_AGE:
                raise ApplicationError(code="VALIDATION_ERROR", field="date_of_birth")

    def _all_satisfied(self, application: Application, uploaded: frozenset[DocumentType]) -> bool:
        """Whether every required row of the checklist is satisfied."""
        marked = self.checklist(application, uploaded)
        return all(row.satisfied for row in marked if row.required)

    def _checklist_counts(
        self, application: Application, uploaded: frozenset[DocumentType]
    ) -> tuple[int, int]:
        """Required and satisfied counts for the summary list (API-030).

        Returns `(0, 0)` for a draft with no property section: there is nothing
        to derive a checklist from yet.
        """
        if application.property_details is None:
            return (0, 0)
        marked = self.checklist(application, uploaded)
        required = [row for row in marked if row.required]
        return (len(required), sum(1 for row in required if row.satisfied))

    def _to_borrower(self, payload: BorrowerRequest) -> Borrower:
        """Convert a wire borrower into the entity."""
        return Borrower(
            full_name=payload.full_name,
            date_of_birth=payload.date_of_birth,
            employment_type=payload.employment_type,
            monthly_net_income=payload.monthly_net_income,
            has_existing_credit=payload.has_existing_credit,
        )

    def _to_property(self, payload: PropertyRequest) -> PropertyDetails:
        """Convert a wire property section into the entity."""
        return PropertyDetails(
            region=payload.region,
            is_first_home=payload.is_first_home,
            property_type=payload.property_type,
            purchase_price=payload.purchase_price,
        )

    def _to_response(
        self, application: Application, uploaded: frozenset[DocumentType]
    ) -> ApplicationResponse:
        """Assemble the full wire body."""
        return ApplicationResponse(
            id=application.id,
            status=application.status,
            simulation_id=application.simulation_id,
            borrowers=[
                BorrowerResponse(
                    id=b.id,
                    full_name=b.full_name,
                    date_of_birth=b.date_of_birth,
                    employment_type=b.employment_type,
                    monthly_net_income=b.monthly_net_income,
                    has_existing_credit=b.has_existing_credit,
                )
                for b in application.borrowers
            ],
            property=self._to_property_response(application),
            submitted_at=application.submitted_at,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )

    def _to_property_response(self, application: Application) -> PropertyResponse | None:
        """Assemble the property section: complete, then partial, then absent.

        A complete `property_details` wins when it exists — that is the
        checklist-ready view. Otherwise fall back to `property_seed`, which is
        set as soon as a simulation seeds the draft even though property_type
        is still unknown (UX-027). Only a genuinely untouched application
        renders `property: null`.
        """
        details = application.property_details
        if details is not None:
            return PropertyResponse(
                region=details.region,
                is_first_home=details.is_first_home,
                property_type=details.property_type,
                purchase_price=details.purchase_price,
            )
        seed = application.property_seed
        if seed is not None:
            return PropertyResponse(
                region=seed.region,
                is_first_home=seed.is_first_home,
                property_type=None,
                purchase_price=seed.purchase_price,
            )
        return None

    def _to_summary(
        self, application: Application, uploaded: frozenset[DocumentType]
    ) -> ApplicationSummary:
        """Assemble one row of the summary list."""
        required, satisfied = self._checklist_counts(application, uploaded)
        return ApplicationSummary(
            id=application.id,
            status=application.status,
            property=self._to_property_response(application),
            documents_required=required,
            documents_satisfied=satisfied,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )


def _to_amount_response(amount: ConfirmedAmount | None) -> ConfirmedAmountResponse | None:
    """Map a confirmed figure onto the wire, provenance included (DOM-029)."""
    if amount is None:
        return None
    return ConfirmedAmountResponse(
        amount=amount.amount,
        provenance=amount.provenance,
        source_document_id=amount.source_document_id,
        confirmed_at=amount.confirmed_at,
    )


def _age_at(birth: date, on: datetime | None = None) -> int:
    """Whole years between a birth date and today (DOM-028)."""
    reference = (on or datetime.now(UTC)).date()
    had_birthday = (reference.month, reference.day) >= (birth.month, birth.day)
    return reference.year - birth.year - (0 if had_birthday else 1)
