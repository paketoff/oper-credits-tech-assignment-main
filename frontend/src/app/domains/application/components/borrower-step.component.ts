import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { Select } from 'primeng/select';

import { EMPLOYMENT_LABELS, optionsOf } from '../../../core/labels';
import { EmploymentType } from '../../../core/models';

export interface BorrowerFormControls {
  full_name: FormControl<string>;
  date_of_birth: FormControl<string>;
  employment_type: FormControl<EmploymentType>;
  monthly_net_income: FormControl<number | null>;
  has_existing_credit: FormControl<boolean>;
}

interface EmploymentOption {
  label: string;
  value: EmploymentType;
}

const EMPLOYMENT_OPTIONS: EmploymentOption[] = optionsOf(EMPLOYMENT_LABELS);

/** Step 1: who is borrowing (`DOM-022`). Dumb — the page owns the form (`ARC-022`). */
@Component({
  selector: 'app-borrower-step',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, Select],
  templateUrl: './borrower-step.component.html',
})
export class BorrowerStepComponent {
  readonly form = input.required<FormGroup<BorrowerFormControls>>();

  protected readonly employmentOptions = EMPLOYMENT_OPTIONS;
}
