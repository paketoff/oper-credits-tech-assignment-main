import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiClient } from '../../core/api-client.service';
import { Simulation, SimulationRequest } from './simulation.models';

const STORAGE_KEY = 'last-simulation-id';

/**
 * HTTP and state for the simulation domain (`ARC-020`). Holds the last
 * simulation id anonymously — the frontend's half of the anonymous-simulation
 * model (`DOM-025`) — so `domains/auth`'s signup form can send it along
 * without either domain reaching into the other's component tree (`ARC-024`).
 *
 * **The id outlives a reload** (`DOM-026`, corrected at T62). Held only in a
 * signal, it was lost the moment the borrower refreshed or typed `/signup`
 * into the address bar: signup still succeeded (`UX-028`), but the draft was
 * created unseeded and the affordability assessment had no instalment to
 * measure against (`API-075`). `sessionStorage`, not `localStorage`: the claim
 * is meant to survive a reload, not to follow the borrower around for weeks
 * on a shared machine.
 *
 * This is not the token `AUTH-053` forbids storing. It is an unguessable UUID4
 * for an anonymous, unclaimed calculation, readable by anyone who has it by
 * design (`API-021`), and it becomes worthless the moment it is claimed
 * (`DOM-027`).
 */
@Injectable({ providedIn: 'root' })
export class SimulationService {
  private readonly api = inject(ApiClient);

  private readonly lastIdSignal = signal<string | null>(sessionStorage.getItem(STORAGE_KEY));
  readonly lastId = this.lastIdSignal.asReadonly();

  simulate(request: SimulationRequest): Observable<Simulation> {
    return this.api
      .post<Simulation>('/simulations', request)
      .pipe(tap((simulation) => this.remember(simulation.id)));
  }

  /** Reads a simulation back — public, since the id is an unguessable UUID4 (`API-021`). */
  get(id: string): Observable<Simulation> {
    return this.api.get<Simulation>(`/simulations/${id}`);
  }

  /** Drop the held id once it has been claimed — it can never be claimed twice (`DOM-027`). */
  forget(): void {
    this.lastIdSignal.set(null);
    sessionStorage.removeItem(STORAGE_KEY);
  }

  private remember(id: string): void {
    this.lastIdSignal.set(id);
    sessionStorage.setItem(STORAGE_KEY, id);
  }
}
