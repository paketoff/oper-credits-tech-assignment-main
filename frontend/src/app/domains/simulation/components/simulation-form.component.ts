import {
  ChangeDetectionStrategy,
  Component,
  DestroyRef,
  OnInit,
  computed,
  inject,
  input,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ReactiveFormsModule, FormGroup, FormControl } from '@angular/forms';
import { InputNumber } from 'primeng/inputnumber';
import { Select } from 'primeng/select';

import { Region } from '../../../core/models';

export interface SimulatorFormControls {
  property_value: FormControl<number>;
  own_contribution: FormControl<number>;
  term_months: FormControl<number>;
  annual_nominal_rate_percent: FormControl<number>;
  region: FormControl<Region>;
  is_first_home: FormControl<boolean>;
}

interface RegionOption {
  label: string;
  value: Region;
}

const REGION_OPTIONS: RegionOption[] = [
  { label: 'Flanders', value: 'FLANDERS' },
  { label: 'Wallonia', value: 'WALLONIA' },
  { label: 'Brussels', value: 'BRUSSELS' },
];

// Same precision as `PercentPipe`'s display of the server's own quotiteit
// figure — rounding each side to 0 decimals independently can make the two
// numbers sum to a visibly different total than the exact one.
const QUOTITEIT_FORMAT = new Intl.NumberFormat('nl-BE', {
  style: 'percent',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

/** `DOM-012`, `DOM-015`: the same formula the backend uses, echoed at the input (`UX-017`). */
function computeQuotiteitHint(propertyValue: number, ownContribution: number): string | null {
  if (!(propertyValue > 0) || !(ownContribution >= 0)) {
    return null;
  }
  const contributionShare = QUOTITEIT_FORMAT.format(ownContribution / propertyValue);
  const quotiteit = QUOTITEIT_FORMAT.format((propertyValue - ownContribution) / propertyValue);
  return `${contributionShare} of the property price → ${quotiteit} quotiteit`;
}

/**
 * The simulator's inputs. Dumb (`ARC-022`): the page owns the form group and
 * this component only renders it — no HTTP, no injected service (`ARC-021`).
 *
 * `p-inputnumber` for the two currency fields and the rate (`UI-036`,
 * locale `nl-BE`); `p-select` for region; everything else is a plain element
 * (`UI-037`).
 */
@Component({
  selector: 'app-simulation-form',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, InputNumber, Select],
  templateUrl: './simulation-form.component.html',
})
export class SimulationFormComponent implements OnInit {
  readonly form = input.required<FormGroup<SimulatorFormControls>>();

  protected readonly regionOptions = REGION_OPTIONS;
  protected readonly Math = Math;

  private readonly destroyRef = inject(DestroyRef);
  private readonly contribution = signal({ property_value: 0, own_contribution: 0 });

  protected readonly quotiteitHint = computed(() => {
    const raw = this.contribution();
    return computeQuotiteitHint(raw.property_value, raw.own_contribution);
  });

  // NG8118: a required input has no value until after construction, so the
  // subscription that feeds `contribution` is wired up here rather than in
  // the constructor.
  ngOnInit(): void {
    const form = this.form();
    const readContribution = (): { property_value: number; own_contribution: number } => ({
      property_value: form.controls.property_value.value,
      own_contribution: form.controls.own_contribution.value,
    });
    this.contribution.set(readContribution());
    form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.contribution.set(readContribution());
    });
  }
}
