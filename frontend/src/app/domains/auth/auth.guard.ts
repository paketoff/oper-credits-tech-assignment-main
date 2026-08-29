import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthState } from '../../core/auth-state.service';

/**
 * Protects the wizard and document routes. Preserves the intended URL so the
 * user lands where they were going after logging in (`AUTH-048`).
 *
 * Safe to read the signal synchronously here: `app.config.ts` blocks
 * bootstrap on `AuthService.resolveSession()`, so by the time the router
 * runs any guard, `AuthState.resolved()` is already true.
 */
export const authGuard: CanActivateFn = (_route, state) => {
  const authState = inject(AuthState);
  const router = inject(Router);

  if (authState.currentUser() !== null) {
    return true;
  }
  return router.createUrlTree(['/login'], { queryParams: { redirect: state.url } });
};
