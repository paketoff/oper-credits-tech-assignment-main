import { Region } from '../../core/models';

/** Mirrors `SimulationRequest` field for field (`API-018`). */
export interface SimulationRequest {
  property_value: string;
  own_contribution: string;
  term_months: number;
  annual_nominal_rate: string;
  region: Region;
  is_first_home: boolean;
}

/** Mirrors `UpfrontCostsResponse` field for field. */
export interface UpfrontCosts {
  registration_duty: string;
  notary_fee: string;
  mortgage_costs: string;
  dossier_fee: string;
  valuation_fee: string;
  total_costs: string;
  own_contribution: string;
  total_cash_needed: string;
}

/** Mirrors `SimulationResponse` field for field (`API-018`, `API-019`). */
export interface Simulation {
  id: string;
  loan_amount: string;
  quotiteit: string;
  above_supervisory_norm: boolean;
  monthly_payment: string;
  total_paid: string;
  total_interest: string;
  nominal_rate: string;
  jkp: string;
  upfront: UpfrontCosts;
  created_at: string;
}
