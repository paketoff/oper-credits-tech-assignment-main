import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { AuthState } from './auth-state.service';
import { errorInterceptor } from './error.interceptor';

describe('errorInterceptor', () => {
  it('redirects to /login preserving the target URL on a 401 (AUTH-048)', () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([errorInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigate').mockResolvedValue(true);
    // The interceptor reads router.url for the URL to preserve; simulate
    // having been on the wizard when the session expired.
    vi.spyOn(router, 'url', 'get').mockReturnValue('/applications/abc-123');

    const http = TestBed.inject(HttpClient);
    const httpMock = TestBed.inject(HttpTestingController);
    http.get('/api/applications/abc-123').subscribe({ error: () => undefined });
    httpMock
      .expectOne('/api/applications/abc-123')
      .flush(
        { code: 'NOT_AUTHENTICATED', message: 'Please sign in.', field: null },
        { status: 401, statusText: 'Unauthorized' },
      );

    expect(navigateSpy).toHaveBeenCalledWith(['/login'], {
      queryParams: { redirect: '/applications/abc-123' },
    });
    httpMock.verify();
  });

  it('clears auth state on a 401', () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([errorInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    const authState = TestBed.inject(AuthState);
    authState.set({ id: 'u1', email: 'jan@example.com', created_at: 'x' });
    vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);

    const http = TestBed.inject(HttpClient);
    const httpMock = TestBed.inject(HttpTestingController);
    http.get('/api/auth/me').subscribe({ error: () => undefined });
    httpMock
      .expectOne('/api/auth/me')
      .flush(
        { code: 'NOT_AUTHENTICATED', message: 'Please sign in.', field: null },
        { status: 401, statusText: 'Unauthorized' },
      );

    expect(authState.currentUser()).toBeNull();
    httpMock.verify();
  });

  it('does not retry, and passes a non-401 failure through unchanged', () => {
    TestBed.configureTestingModule({
      providers: [
        provideRouter([]),
        provideHttpClient(withInterceptors([errorInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    const http = TestBed.inject(HttpClient);
    const httpMock = TestBed.inject(HttpTestingController);
    let seenStatus: number | undefined;
    http.get('/api/simulations/x').subscribe({
      error: (error: { status: number }) => {
        seenStatus = error.status;
      },
    });

    httpMock
      .expectOne('/api/simulations/x')
      .flush(
        { code: 'SIMULATION_NOT_FOUND', message: 'Simulation not found.', field: null },
        { status: 404, statusText: 'Not Found' },
      );

    expect(seenStatus).toBe(404);
    httpMock.verify();
  });
});
