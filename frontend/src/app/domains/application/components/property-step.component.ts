import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { InputNumber } from 'primeng/inputnumber';
import { Select } from 'primeng/select';

import { PropertyType, Region } from '../../../core/models';

export interface PropertyFormControls {
  region: FormControl<Region>;
  is_first_home: FormControl<boolean>;
  property_type: FormControl<PropertyType>;
  purchase_price: FormControl<number>;
}

const REGION_OPTIONS = [
  { label: 'Flanders', value: 'FLANDERS' as Region },
  { label: 'Wallonia', value: 'WALLONIA' as Region },
  { label: 'Brussels', value: 'BRUSSELS' as Region },
];

const PROPERTY_TYPE_OPTIONS = [
  { label: 'Existing', value: 'EXISTING' as PropertyType },
  { label: 'New build', value: 'NEW_BUILD' as PropertyType },
];

/** Step 2: the property (`DOM-024`). Dumb — the page owns the form (`ARC-022`). */
@Component({
  selector: 'app-property-step',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, Select, InputNumber],
  templateUrl: './property-step.component.html',
})
export class PropertyStepComponent {
  readonly form = input.required<FormGroup<PropertyFormControls>>();

  protected readonly regionOptions = REGION_OPTIONS;
  protected readonly propertyTypeOptions = PROPERTY_TYPE_OPTIONS;
}
