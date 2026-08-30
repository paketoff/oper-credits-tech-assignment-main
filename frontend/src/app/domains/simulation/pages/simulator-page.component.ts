import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import {
  EMPTY,
  catchError,
  debounceTime,
  distinctUntilChanged,
  filter,
  map,
  merge,
  of,
  switchMap,
} from 'rxjs';

import { ApiError, apiErrorOf } from '../../../core/error-codes';
import { Region } from '../../../core/models';
import {
  SimulationFormComponent,
  SimulatorFormControls,
} from '../components/simulation-form.component';
import { SimulationResultComponent } from '../components/simulation-result.component';
import { Simulation, SimulationRequest } from '../simulation.models';
import { SimulationService } from '../simulation.service';

// UX-009, UX-010: the exact six inputs of AC-003. The opening screen and the
// test suite assert the same numbers on purpose — if the prefill changes,
// AC-003 changes with it, and neither moves alone.
const PRIMARY_CASE = {
  property_value: 300_000,
  own_contribution: 30_000,
  term_months: 300,
  annual_nominal_rate_percent: 4.0,
  region: 'FLANDERS' as Region,
  is_first_home: true,
};

const DEBOUNCE_MS = 300;

interface RawFormValue {
  property_value: number;
  own_contribution: number;
  term_months: number;
  annual_nominal_rate_percent: number;
  region: Region;
  is_first_home: boolean;
}

function toRequest(value: RawFormValue): SimulationRequest {
  return {
    property_value: value.property_value.toFixed(2),
    own_contribution: value.own_contribution.toFixed(2),
    term_months: value.term_months,
    annual_nominal_rate: (value.annual_nominal_rate_percent / 100).toFixed(4),
    region: value.region,
    is_first_home: value.is_first_home,
  };
}

/**
 * The public simulator: prefilled and computed on first paint, no button
 * (`UX-009` – `UX-014`). Two columns from `md:` up, stacked on mobile
 * (`UI-054`).
 */
@Component({
  selector: 'app-simulator-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [SimulationFormComponent, SimulationResultComponent],
  templateUrl: './simulator-page.component.html',
})
export class SimulatorPageComponent {
  private readonly simulationService = inject(SimulationService);

  readonly form = new FormGroup<SimulatorFormControls>({
    property_value: new FormControl(PRIMARY_CASE.property_value, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(10_000), Validators.max(10_000_000)],
    }),
    own_contribution: new FormControl(PRIMARY_CASE.own_contribution, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(0)],
    }),
    term_months: new FormControl(PRIMARY_CASE.term_months, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(12), Validators.max(360)],
    }),
    annual_nominal_rate_percent: new FormControl(PRIMARY_CASE.annual_nominal_rate_percent, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(0), Validators.max(20)],
    }),
    region: new FormControl(PRIMARY_CASE.region, { nonNullable: true }),
    is_first_home: new FormControl(PRIMARY_CASE.is_first_home, { nonNullable: true }),
  });

  protected readonly result = signal<Simulation | null>(null);
  protected readonly loading = signal(false);
  /**
   * `UX-023`, `UX-024`, `VAL-027` step 4. A contribution equal to the price
   * passes every client-side validator — it is only the *server* that knows a
   * loan of zero is not a loan — so without this the request went out, came
   * back 422 `LOAN_AMOUNT_NOT_POSITIVE`, and was swallowed: the borrower saw
   * the previous result sitting there and no explanation at all.
   */
  protected readonly error = signal<ApiError | null>(null);

  constructor() {
    // The initial value bypasses debounceTime entirely, so first paint never
    // waits on the 300ms window (UX-009, UX-055); every later change goes
    // through it (UX-012). Both funnel through one switchMap, so a value
    // typed while the first request is still in flight cancels it rather
    // than racing it (UX-014) — the previous *result* is never cleared while
    // that happens (UX-013, UX-056).
    const initial$ = of(this.form.getRawValue());
    const changes$ = this.form.valueChanges.pipe(
      map(() => this.form.getRawValue()),
      debounceTime(DEBOUNCE_MS),
    );

    merge(initial$, changes$)
      .pipe(
        // UX-063: a transient invalid value (e.g. a field cleared mid-edit)
        // never reaches the network — the previous valid result just stays
        // on screen (UX-013) instead of the request going out and failing.
        filter(() => this.form.valid),
        distinctUntilChanged((a, b) => JSON.stringify(a) === JSON.stringify(b)),
        switchMap((value) => {
          this.loading.set(true);
          return this.simulationService.simulate(toRequest(value)).pipe(
            // UX-063: caught here, inside the switchMap, not at the outer
            // subscribe — an uncaught error there would terminate the whole
            // subscription permanently, silently freezing every future
            // recompute rather than just failing this one request.
            catchError((failure: unknown) => {
              this.error.set(apiErrorOf(failure));
              this.loading.set(false);
              return EMPTY;
            }),
          );
        }),
        takeUntilDestroyed(),
      )
      .subscribe((simulation) => {
        this.result.set(simulation);
        this.error.set(null);
        this.loading.set(false);
      });
  }
}
