/**
 * Value types shared across domains — the frontend twin of `core/enums.py`
 * (`ARC-044`). Mirrors the wire format field for field, no renaming layer
 * (`API-059`, `ARC-027`).
 */

export type Region = 'FLANDERS' | 'WALLONIA' | 'BRUSSELS';
export type PropertyType = 'EXISTING' | 'NEW_BUILD';
export type EmploymentType = 'EMPLOYEE' | 'SELF_EMPLOYED' | 'OTHER';

export type ApplicationStatus =
  | 'DRAFT'
  | 'SUBMITTED'
  | 'DOCUMENTS_PENDING'
  | 'DOCUMENTS_COMPLETE'
  | 'UNDER_REVIEW'
  | 'OFFER_ISSUED'
  | 'WITHDRAWN';
