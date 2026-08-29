import { HttpContextToken } from '@angular/common/http';

/**
 * Opts a request out of `error.interceptor.ts`'s redirect-to-login on a 401.
 *
 * The boot-time `GET /api/auth/me` (`AUTH-046`) genuinely expects a 401 for
 * every anonymous visitor — the simulator is a public route and that is the
 * normal case, not a lost session. Without this, a first-time visitor to `/`
 * would be redirected straight to `/login` before ever seeing the app,
 * because the interceptor cannot otherwise tell "checking whether a session
 * exists" apart from "an authenticated action's session just expired"
 * (`AUTH-047`).
 */
export const SKIP_AUTH_REDIRECT = new HttpContextToken<boolean>(() => false);
