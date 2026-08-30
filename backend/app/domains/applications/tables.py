"""SQLAlchemy definitions of the applications and borrowers tables."""

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

_MONEY = Numeric(12, 2)


class ApplicationRow(Base):
    """A borrower's mortgage file.

    The property columns are nullable because an application starts as a draft
    and is filled step by step: only the current step validates, and full
    validation runs once on submit (UX-032, VAL-012). Requiring them at insert
    would make the draft unsaveable, which is what UX-033 exists to prevent.
    """

    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    simulation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("simulations.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(32))
    region: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_first_home: Mapped[bool | None] = mapped_column(nullable=True)
    property_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    purchase_price: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    borrowers: Mapped[list["BorrowerRow"]] = relationship(
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="BorrowerRow.created_at",
    )


class FinancialProfileRow(Base):
    """The confirmed figures the affordability assessment reads (DOM-029).

    **A separate table, not columns on `borrowers`.** API-037 replaces the
    borrower collection wholesale on every PATCH, so a figure stored there is
    destroyed the next time the borrower edits the wizard — which is exactly
    what must not happen to a number they confirmed off a document.

    One row per application, so `application_id` is the primary key: there is
    nothing to say about a second profile for the same file.

    The provenance columns are flat rather than a JSON blob for the same reason
    `borrowers` is a table (CQ-085): "which figures came from a document" is a
    question worth being able to ask in SQL.
    """

    __tablename__ = "application_financials"

    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), primary_key=True
    )

    net_monthly_income: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    net_monthly_income_provenance: Mapped[str | None] = mapped_column(String(16), nullable=True)
    net_monthly_income_source_document_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    net_monthly_income_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    existing_credit_monthly: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    existing_credit_provenance: Mapped[str | None] = mapped_column(String(16), nullable=True)
    existing_credit_source_document_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True)
    existing_credit_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    dependants: Mapped[int] = mapped_column(default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class BorrowerRow(Base):
    """One person on an application.

    **A real table, not a JSON column.** Most Belgian mortgages are joint
    (DOM-021), and one-to-many is exactly the relation a relational model exists
    for — a JSON blob would make "any borrower is self-employed" a scan in
    Python instead of a query (CQ-085).
    """

    __tablename__ = "borrowers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("applications.id", ondelete="CASCADE"), index=True
    )
    full_name: Mapped[str] = mapped_column(String(200))
    date_of_birth: Mapped[date] = mapped_column(Date)
    employment_type: Mapped[str] = mapped_column(String(20))
    monthly_net_income: Mapped[Decimal | None] = mapped_column(_MONEY, nullable=True)
    has_existing_credit: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    application: Mapped[ApplicationRow] = relationship(back_populates="borrowers")
