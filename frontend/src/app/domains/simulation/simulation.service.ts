import { Injectable, inject, signal } from '@angular/core';
import { Observable, tap } from 'rxjs';

import { ApiClient } from '../../core/api-client.service';
import { Simulation, SimulationRequest } from './simulation.models';

/**
 * HTTP and state for the simulation domain (`ARC-020`). Holds the last
 * simulation id anonymously — the frontend's half of the anonymous-simulation
 * model (`DOM-025`) — so `domains/auth`'s signup form can send it along
 * without either domain reaching into the other's component tree (`ARC-024`).
 */
@Injectable({ providedIn: 'root' })
export class SimulationService {
  private readonly api = inject(ApiClient);

  private readonly lastIdSignal = signal<string | null>(null);
  readonly lastId = this.lastIdSignal.asReadonly();

  simulate(request: SimulationRequest): Observable<Simulation> {
    return this.api
      .post<Simulation>('/simulations', request)
      .pipe(tap((simulation) => this.lastIdSignal.set(simulation.id)));
  }

  /** Reads a simulation back — public, since the id is an unguessable UUID4 (`API-021`). */
  get(id: string): Observable<Simulation> {
    return this.api.get<Simulation>(`/simulations/${id}`);
  }
}
