"""SQLAlchemy definition of the simulations table."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# CQ-086. Money is Numeric(12, 2) and reads back as Decimal, never float.
# Rates carry four decimals because that is what crosses the wire (API-005).
_MONEY = Numeric(12, 2)
_RATE = Numeric(6, 4)


class SimulationRow(Base):
    """A stored simulation. Never leaves the repository (CQ-088).

    Only the inputs are persisted. Payment, JKP, quotiteit and the cost
    breakdown are all functions of these columns and are recomputed on read —
    storing them invites drift between what was saved and what the rules say
    (DOM-001, DOM-009).
    """

    __tablename__ = "simulations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    # Nullable, and indexed: a simulation is anonymous until someone signs up
    # (DOM-008), and the claim looks it up by owner afterwards.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    property_value: Mapped[Decimal] = mapped_column(_MONEY)
    own_contribution: Mapped[Decimal] = mapped_column(_MONEY)
    term_months: Mapped[int]
    annual_nominal_rate: Mapped[Decimal] = mapped_column(_RATE)
    region: Mapped[str] = mapped_column(String(16))
    is_first_home: Mapped[bool]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
