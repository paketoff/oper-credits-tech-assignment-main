/**
 * Mirrors `ApplicationCreateRequest` (`API-032`). The rest of the application
 * domain's models — the full response, the wizard's per-step bodies — land
 * with T29's wizard; this is the one shape T28's signup flow needs to seed a
 * draft from the simulation it just claimed.
 */
export interface ApplicationCreateRequest {
  simulation_id: string | null;
}

/** The one field the signup flow needs back: where to send the borrower next. */
export interface CreatedApplication {
  id: string;
}
