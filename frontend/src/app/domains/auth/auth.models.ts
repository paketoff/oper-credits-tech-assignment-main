import { User } from '../../core/auth-state.service';

/** Mirrors `SignupRequest` field for field (`API-023`). */
export interface SignupRequest {
  email: string;
  password: string;
  simulation_id: string | null;
}

/** Mirrors `LoginRequest` field for field (`API-026`). */
export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * Mirrors `SignupResponse` (`API-023`, corrected at T17): no `application_id`
 * — signup only claims a simulation, `POST /api/applications` creates the
 * draft next.
 */
export interface SignupResponse {
  user: User;
  claimed_simulation_id: string | null;
}

/** Mirrors `LoginResponse` field for field (`API-026`). */
export interface LoginResponse {
  user: User;
}
