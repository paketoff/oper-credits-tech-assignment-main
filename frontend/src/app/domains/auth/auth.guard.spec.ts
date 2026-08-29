import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { AuthState } from '../../core/auth-state.service';
import { authGuard } from './auth.guard';

describe('authGuard', () => {
  it('allows a signed-in borrower through', () => {
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    const authState = TestBed.inject(AuthState);
    authState.set({ id: 'u1', email: 'jan@example.com', created_at: 'x' });

    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as never, { url: '/applications/abc' } as never),
    );

    expect(result).toBe(true);
  });

  it('redirects to /login preserving the intended URL (AUTH-048)', () => {
    TestBed.configureTestingModule({ providers: [provideRouter([])] });

    const result = TestBed.runInInjectionContext(() =>
      authGuard({} as never, { url: '/applications/abc-123' } as never),
    );

    const router = TestBed.inject(Router);
    const expected = router.createUrlTree(['/login'], {
      queryParams: { redirect: '/applications/abc-123' },
    });
    expect(router.serializeUrl(result as never)).toBe(router.serializeUrl(expected));
  });
});
