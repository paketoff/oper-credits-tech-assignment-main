import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, of, tap } from 'rxjs';

import { HttpContext } from '@angular/common/http';

import { ApiClient } from '../../core/api-client.service';
import { AuthState } from '../../core/auth-state.service';
import { SKIP_AUTH_REDIRECT } from '../../core/http-context';
import { LoginRequest, LoginResponse, SignupRequest, SignupResponse } from './auth.models';

/**
 * HTTP for the auth domain. `core/auth-state.service.ts` holds the signal;
 * this is the only thing that writes to it via the network (`AUTH-046`).
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly api = inject(ApiClient);
  private readonly authState = inject(AuthState);

  signup(request: SignupRequest): Observable<SignupResponse> {
    return this.api
      .post<SignupResponse>('/auth/signup', request)
      .pipe(tap((response) => this.authState.set(response.user)));
  }

  login(request: LoginRequest): Observable<LoginResponse> {
    return this.api
      .post<LoginResponse>('/auth/login', request)
      .pipe(tap((response) => this.authState.set(response.user)));
  }

  logout(): Observable<void> {
    // AUTH-028: succeeds whether or not a session existed. The httpOnly
    // cookie only clears server-side, so this always hits the endpoint
    // rather than merely forgetting the local signal.
    return this.api.post<void>('/auth/logout', {}).pipe(tap(() => this.authState.clear()));
  }

  /**
   * Resolves the boot-time auth state from the one endpoint the frontend can
   * use to ask, since it cannot read the httpOnly cookie itself (`AUTH-029`,
   * `AUTH-046`). Never errors outward: an absent or expired session is a
   * normal "not signed in", not a failure the app initializer should block
   * startup on.
   */
  resolveSession(): Observable<void> {
    const skipRedirect = new HttpContext().set(SKIP_AUTH_REDIRECT, true);
    return this.api
      .get<{ id: string; email: string; created_at: string }>('/auth/me', undefined, skipRedirect)
      .pipe(
        tap((user) => this.authState.set(user)),
        map(() => undefined),
        catchError(() => {
          this.authState.clear();
          return of(undefined);
        }),
      );
  }
}
