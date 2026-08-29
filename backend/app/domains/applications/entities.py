"""Domain types for applications, borrowers and the property.

Frozen dataclasses and enums. Not the wire schemas, which are pydantic and live
in `schemas.py` (ARC-040).
"""

from enum import StrEnum


class ApplicationStatus(StrEnum):
    """Where an application sits in its lifecycle (0-business-logic.md §12).

    Single-domain, so it lives here rather than in `core/enums.py` (ARC-044).

    `UNDER_REVIEW` collapses three distinct real-world gates — property
    valuation, CKP credit-register consultation, and credit assessment. Named as
    one state with this comment rather than silently omitted (APP-010, SCP-018).
    """

    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    DOCUMENTS_PENDING = "DOCUMENTS_PENDING"
    DOCUMENTS_COMPLETE = "DOCUMENTS_COMPLETE"
    UNDER_REVIEW = "UNDER_REVIEW"
    OFFER_ISSUED = "OFFER_ISSUED"
    WITHDRAWN = "WITHDRAWN"
