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
