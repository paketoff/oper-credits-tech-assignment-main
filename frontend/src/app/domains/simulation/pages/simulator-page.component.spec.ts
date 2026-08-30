import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { Simulation } from '../simulation.models';
import { SimulatorPageComponent } from './simulator-page.component';

// AC-003, mirrored — a real body shaped like what the backend actually returns.
function primarySimulation(overrides: Partial<Simulation> = {}): Simulation {
  return {
    id: 'sim-1',
    loan_amount: '270000.00',
    quotiteit: '0.9000',
    above_supervisory_norm: false,
    monthly_payment: '1414.52',
    total_paid: '424356.04',
    total_interest: '154356.04',
    nominal_rate: '0.0400',
    jkp: '0.0414',
    upfront: {
      registration_duty: '6000.00',
      notary_fee: '3300.00',
      mortgage_costs: '3240.00',
      dossier_fee: '350.00',
      valuation_fee: '285.00',
      total_costs: '13175.00',
      own_contribution: '30000.00',
      total_cash_needed: '43175.00',
    },
    created_at: '2026-08-29T00:00:00Z',
    ...overrides,
  };
}

describe('SimulatorPageComponent', () => {
  let httpMock: HttpTestingController;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [SimulatorPageComponent],
      providers: [provideRouter([]), provideHttpClient(), provideHttpClientTesting()],
    }).compileComponents();
    httpMock = TestBed.inject(HttpTestingController);
  });

  it('renders a computed result on first paint, with no interaction', () => {
    const fixture = TestBed.createComponent(SimulatorPageComponent);
    fixture.detectChanges();

    // No debounce on the initial value: the request fires synchronously on
    // construction, before any timer, and `expectOne` fails outright if it
    // does not — this app is zoneless, so `flush` resolves the subscription
    // straight away with no microtask flush needed.
    httpMock.expectOne('/api/simulations').flush(primarySimulation());
    fixture.detectChanges();

    const rendered = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(rendered).toContain('1.414,52');
    httpMock.verify();
  });

  it('keeps the previous result visible while a new one is loading', () => {
    vi.useFakeTimers();
    try {
      const fixture = TestBed.createComponent(SimulatorPageComponent);
      fixture.detectChanges();
      httpMock.expectOne('/api/simulations').flush(primarySimulation());
      fixture.detectChanges();

      fixture.componentInstance.form.controls.own_contribution.setValue(0);
      vi.advanceTimersByTime(300);
      fixture.detectChanges();

      // The request is in flight and the panel is dimmed, but the OLD
      // figure is still on screen — the assertion UX-013/UX-056 exist for.
      const compiled = fixture.nativeElement as HTMLElement;
      expect(compiled.textContent).toContain('1.414,52');
      expect(compiled.querySelector('.opacity-60')).toBeTruthy();

      httpMock
        .expectOne('/api/simulations')
        .flush(primarySimulation({ quotiteit: '1.0000', above_supervisory_norm: true }));
      fixture.detectChanges();

      expect(compiled.querySelector('.opacity-60')).toBeFalsy();
      httpMock.verify();
    } finally {
      vi.useRealTimers();
    }
  });

  it('shows the above-norm chip once quotiteit crosses 90%, styled as informational', () => {
    const fixture = TestBed.createComponent(SimulatorPageComponent);
    fixture.detectChanges();
    httpMock
      .expectOne('/api/simulations')
      .flush(primarySimulation({ above_supervisory_norm: true }));
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    const chip = compiled.querySelector('[role="status"]');

    expect(chip?.textContent).toContain('90%');
    // UI-050: informational, never styled as an error.
    expect(chip?.className).not.toContain('danger');
    httpMock.verify();
  });

  it('an invalid intermediate value never reaches the network, and recompute resumes after (UX-063)', () => {
    vi.useFakeTimers();
    try {
      const fixture = TestBed.createComponent(SimulatorPageComponent);
      fixture.detectChanges();
      httpMock.expectOne('/api/simulations').flush(primarySimulation());
      fixture.detectChanges();

      // Mirrors what the browser's own number input reports when the field
      // is cleared mid-edit — not NaN, `null` (Angular's NumberValueAccessor).
      fixture.componentInstance.form.controls.term_months.setValue(null as unknown as number);
      vi.advanceTimersByTime(300);
      fixture.detectChanges();
      httpMock.expectNone('/api/simulations');

      // A further, genuinely different edit — this used to stay frozen
      // forever because the earlier, uncaught request failure had already
      // killed the subscription (the real bug the user reported).
      fixture.componentInstance.form.controls.term_months.setValue(240);
      vi.advanceTimersByTime(300);
      fixture.detectChanges();
      httpMock
        .expectOne('/api/simulations')
        .flush(primarySimulation({ monthly_payment: '999.99' }));
      fixture.detectChanges();

      expect((fixture.nativeElement as HTMLElement).textContent).toContain('999,99');
      httpMock.verify();
    } finally {
      vi.useRealTimers();
    }
  });

  it('a failed request does not stop future recomputation (UX-063)', () => {
    vi.useFakeTimers();
    try {
      const fixture = TestBed.createComponent(SimulatorPageComponent);
      fixture.detectChanges();
      httpMock.expectOne('/api/simulations').flush(primarySimulation());
      fixture.detectChanges();

      fixture.componentInstance.form.controls.own_contribution.setValue(50_000);
      vi.advanceTimersByTime(300);
      fixture.detectChanges();
      httpMock
        .expectOne('/api/simulations')
        .flush(
          { code: 'VALIDATION_ERROR', message: 'Check the highlighted fields.', field: null },
          { status: 422, statusText: 'Unprocessable Entity' },
        );
      fixture.detectChanges();

      fixture.componentInstance.form.controls.own_contribution.setValue(60_000);
      vi.advanceTimersByTime(300);
      fixture.detectChanges();
      httpMock
        .expectOne('/api/simulations')
        .flush(primarySimulation({ monthly_payment: '888.88' }));
      fixture.detectChanges();

      expect((fixture.nativeElement as HTMLElement).textContent).toContain('888,88');
      httpMock.verify();
    } finally {
      vi.useRealTimers();
    }
  });

  it('renders the server message beside the field the response named (UX-024)', () => {
    // VAL-027 step 4: a contribution equal to the price is valid to every
    // client-side rule, so only the server can reject it. Before this, the
    // 422 was swallowed and the borrower saw the stale result and nothing
    // else.
    vi.useFakeTimers();
    try {
      const fixture = TestBed.createComponent(SimulatorPageComponent);
      fixture.detectChanges();
      httpMock.expectOne('/api/simulations').flush(primarySimulation());
      fixture.detectChanges();

      fixture.componentInstance.form.controls.own_contribution.setValue(300_000);
      vi.advanceTimersByTime(300);
      fixture.detectChanges();
      httpMock.expectOne('/api/simulations').flush(
        {
          code: 'LOAN_AMOUNT_NOT_POSITIVE',
          message: 'Your own contribution must be less than the property price.',
          field: 'own_contribution',
        },
        { status: 422, statusText: 'Unprocessable Entity' },
      );
      fixture.detectChanges();

      const contributionField = (fixture.nativeElement as HTMLElement)
        .querySelector('#own_contribution')
        ?.closest('div');
      expect(contributionField?.textContent).toContain('must be less than the property price');
      httpMock.verify();
    } finally {
      vi.useRealTimers();
    }
  });
});
