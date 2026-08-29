import { HttpInterceptorFn } from '@angular/common/http';

/**
 * Structural placeholder matching `ARC-020`'s tree. No bearer token is ever
 * attached — the session travels as an httpOnly cookie the frontend cannot
 * read (`AUTH-001`, `AUTH-044`) — so this passes every request through
 * unchanged. It exists as the one place a future auth header would be added
 * without touching `api-client.service.ts` or the other interceptor.
 */
export const authInterceptor: HttpInterceptorFn = (request, next) => next(request);
