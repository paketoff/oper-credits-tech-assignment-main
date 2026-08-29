import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../../core/api-client.service';
import {
  Application,
  ApplicationCreateRequest,
  ApplicationList,
  ApplicationPatchRequest,
} from './application.models';

/**
 * HTTP and state for the application domain (`ARC-020`). `create()` is the
 * signup flow's cross-domain hand-off (T28); `get`/`patch`/`submit` are the
 * wizard's (T29); `list()` backs the "my applications" screen (T52).
 */
@Injectable({ providedIn: 'root' })
export class ApplicationService {
  private readonly api = inject(ApiClient);

  /** A borrower has one or two applications — no pagination (`API-031`). */
  list(): Observable<ApplicationList> {
    return this.api.get<ApplicationList>('/applications');
  }

  create(request: ApplicationCreateRequest): Observable<Application> {
    return this.api.post<Application>('/applications', request);
  }

  get(id: string): Observable<Application> {
    return this.api.get<Application>(`/applications/${id}`);
  }

  /** Only present keys are sent and only they are validated (`API-036`, `UX-032`). */
  patch(id: string, request: ApplicationPatchRequest): Observable<Application> {
    return this.api.patch<Application>(`/applications/${id}`, request);
  }

  /** Runs full validation across every step, then transitions the application (`API-041`). */
  submit(id: string): Observable<Application> {
    return this.api.post<Application>(`/applications/${id}/submit`, {});
  }
}
