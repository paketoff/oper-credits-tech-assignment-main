import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, throwError } from 'rxjs';

import { AuthState } from './auth-state.service';
import { SKIP_AUTH_REDIRECT } from './http-context';

/**
 * Catches a 401 globally, clears auth state, redirects to login. Does not
 * retry (`AUTH-047`). Preserves the URL the borrower was trying to reach so
 * the login page can send them back afterwards (`AUTH-048`).
 *
 * The redirect is skipped for a request carrying `SKIP_AUTH_REDIRECT` —
 * the boot-time `/auth/me` check, which gets a 401 for every anonymous
 * visitor to a public route and must not send them to `/login` before they
 * have even seen the app. Auth state is still cleared either way: a 401 is a
 * 401 regardless of which request produced it.
 *
 * Every other failure passes through unchanged: a domain error's `{code,
 * message, field}` body is for the component that made the call to render
 * beside its own field (`UX-024`), not for this interceptor to interpret.
 */
export const errorInterceptor: HttpInterceptorFn = (request, next) => {
  const authState = inject(AuthState);
  const router = inject(Router);

  return next(request).pipe(
    catchError((error: unknown) => {
      if (error instanceof HttpErrorResponse && error.status === 401) {
        authState.clear();
        if (!request.context.get(SKIP_AUTH_REDIRECT)) {
          void router.navigate(['/login'], { queryParams: { redirect: router.url } });
        }
      }
      return throwError(() => error);
    }),
  );
};
