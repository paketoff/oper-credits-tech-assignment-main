import { ApplicationStatus, EmploymentType, PropertyType, Region } from '../../core/models';

/** Mirrors `ApplicationCreateRequest` (`API-032`). */
export interface ApplicationCreateRequest {
  simulation_id: string | null;
}

/** Mirrors `BorrowerRequest` (`API-035`). No `id`: a PATCH replaces the collection wholesale. */
export interface BorrowerRequest {
  full_name: string;
  date_of_birth: string;
  employment_type: EmploymentType;
  monthly_net_income: string | null;
  has_existing_credit: boolean;
}

/** Mirrors `BorrowerResponse` field for field. */
export interface Borrower extends BorrowerRequest {
  id: string;
}

/** Mirrors `PropertyRequest` (`API-035`). */
export interface PropertyRequest {
  region: Region;
  is_first_home: boolean;
  property_type: PropertyType;
  purchase_price: string;
}

/**
 * Mirrors `PropertyResponse` (`API-071`, corrected at T21). `property_type`
 * is nullable: a simulation-seeded draft has a region and a price before the
 * borrower has said existing-vs-new-build.
 */
export interface PropertyDetails {
  region: Region;
  is_first_home: boolean;
  property_type: PropertyType | null;
  purchase_price: string;
}

/** Mirrors `ApplicationPatchRequest` (`API-035`). Only present keys are sent (`API-036`). */
export interface ApplicationPatchRequest {
  /** Attaches a simulation after the fact; the server checks it is claimable. */
  simulation_id?: string;
  borrowers?: BorrowerRequest[];
  property?: PropertyRequest;
}

/** Mirrors `ApplicationResponse` field for field (`API-033`). */
export interface Application {
  id: string;
  status: ApplicationStatus;
  simulation_id: string | null;
  borrowers: Borrower[];
  property: PropertyDetails | null;
  submitted_at: string | null;
  created_at: string;
  updated_at: string;
}

/** One row of `GET /api/applications` (`API-029`, `API-030`) — a summary, not a full body. */
export interface ApplicationSummary {
  id: string;
  status: ApplicationStatus;
  property: PropertyDetails | null;
  documents_required: number;
  documents_satisfied: number;
  created_at: string;
  updated_at: string;
}

/** Mirrors `ApplicationListResponse` (`API-030`). */
export interface ApplicationList {
  items: ApplicationSummary[];
}

/** Mirrors `Provenance` (`DOM-029`). `DOCUMENT` means the borrower confirmed what a document said. */
export type Provenance = 'MANUAL' | 'DOCUMENT';

/** Mirrors `ConfirmedAmountResponse` field for field (`API-074`). */
export interface ConfirmedAmount {
  amount: string;
  provenance: Provenance;
  source_document_id: string | null;
  confirmed_at: string;
}

/** Mirrors `AffordabilityBand` (`SIM-028`). A band, never a decision. */
export type AffordabilityBand =
  'COMFORTABLE' | 'TIGHT' | 'OUTSIDE_TYPICAL_NORMS' | 'INSUFFICIENT_DATA';

/** Mirrors `AffordabilityResponse` field for field (`API-074`, `API-076`). */
export interface Affordability {
  band: AffordabilityBand;
  dsti: string | null;
  monthly_obligations: string;
  residual_income: string | null;
  residual_floor: string;
}

/** Mirrors `FinancialsRequest` (`API-073`). Values only — the server records provenance. */
export interface FinancialsRequest {
  net_monthly_income: string | null;
  existing_credit_monthly: string | null;
  dependants: number;
}

/** Mirrors `FinancialsResponse` field for field (`API-074`, `API-075`). */
export interface Financials {
  net_monthly_income: ConfirmedAmount | null;
  existing_credit_monthly: ConfirmedAmount | null;
  dependants: number;
  assessment: Affordability | null;
  updated_at: string | null;
}
