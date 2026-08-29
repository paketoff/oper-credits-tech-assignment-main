import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from '../../core/api-client.service';
import { ApplicationCreateRequest, CreatedApplication } from './application.models';

/**
 * HTTP and state for the application domain (`ARC-020`). Only `create()` so
 * far — the signup flow's cross-domain hand-off, the frontend's counterpart
 * to the backend's `ARC-047` edge. T29 expands this with list, get, patch and
 * submit as the wizard is built.
 */
@Injectable({ providedIn: 'root' })
export class ApplicationService {
  private readonly api = inject(ApiClient);

  create(request: ApplicationCreateRequest): Observable<CreatedApplication> {
    return this.api.post<CreatedApplication>('/applications', request);
  }
}
