import { ChangeDetectionStrategy, Component, input } from '@angular/core';
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
export class SimulationFormComponent {
  readonly form = input.required<FormGroup<SimulatorFormControls>>();

  protected readonly regionOptions = REGION_OPTIONS;
  protected readonly Math = Math;
}
