import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';

import { SimulationService } from '../../simulation/simulation.service';
import { SignupPageComponent } from './signup-page.component';

function submitForm(fixture: ReturnType<typeof TestBed.createComponent>): void {
  (fixture.nativeElement as HTMLElement)
    .querySelector('form')
    ?.dispatchEvent(new Event('submit', { cancelable: true, bubbles: true }));
}

describe('SignupPageComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SignupPageComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    httpMock = TestBed.inject(HttpTestingController);
    // The test router has no routes registered; only the request contents
    // are under test here, not the navigation itself.
    vi.spyOn(TestBed.inject(Router), 'navigate').mockResolvedValue(true);
  });

  it('sends the anonymous simulation id from the simulator (AUTH-049)', () => {
    const fixture = TestBed.createComponent(SignupPageComponent);
    const simulationService = TestBed.inject(SimulationService);
    // Simulates the borrower having already run a simulation on this visit,
    // the way SimulationService.simulate() sets it on a real 201 response.
    vi.spyOn(simulationService, 'lastId').mockReturnValue('sim-abc-123');
    fixture.detectChanges();

    fixture.componentInstance.form.setValue({
      email: 'jan@example.com',
      password: 'hunter2hunter2',
    });
    submitForm(fixture);

    const request = httpMock.expectOne('/api/auth/signup');
    expect(request.request.body).toEqual({
      email: 'jan@example.com',
      password: 'hunter2hunter2',
      simulation_id: 'sim-abc-123',
    });
    request.flush({
      user: { id: 'u1', email: 'jan@example.com', created_at: 'x' },
      claimed_simulation_id: 'sim-abc-123',
    });

    httpMock.expectOne('/api/applications').flush({ id: 'app-1' });
    httpMock.verify();
  });

  it('sends null when no simulation was ever run', () => {
    const fixture = TestBed.createComponent(SignupPageComponent);
    fixture.detectChanges();

    fixture.componentInstance.form.setValue({
      email: 'nobody@example.com',
      password: 'hunter2hunter2',
    });
    submitForm(fixture);

    const request = httpMock.expectOne('/api/auth/signup');
    expect(request.request.body.simulation_id).toBeNull();
    request.flush({
      user: { id: 'u2', email: 'nobody@example.com', created_at: 'x' },
      claimed_simulation_id: null,
    });

    httpMock.expectOne('/api/applications').flush({ id: 'app-2' });
    httpMock.verify();
  });
});
