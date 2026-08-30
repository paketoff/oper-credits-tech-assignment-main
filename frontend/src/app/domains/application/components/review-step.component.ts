import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

import { EMPLOYMENT_LABELS, REGION_LABELS } from '../../../core/labels';
import { MoneyPipe } from '../../../shared/money.pipe';
import { Simulation } from '../../simulation/simulation.models';
import { Application } from '../application.models';

/**
 * Step 4: review and submit. Each section links back to its own step
 * (`UX-034`) and returns to review afterwards — the page owns that
 * navigation, this component only emits which step was chosen (`ARC-022`).
 */
@Component({
  selector: 'app-review-step',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MoneyPipe],
  templateUrl: './review-step.component.html',
})
export class ReviewStepComponent {
  /** The last screen before submission read `FLANDERS` and `EMPLOYEE` out loud. */
  protected readonly regionLabels = REGION_LABELS;
  protected readonly employmentLabels = EMPLOYMENT_LABELS;

  readonly application = input.required<Application>();
  readonly simulation = input<Simulation | null>(null);
  readonly submitting = input(false);

  readonly editStep = output<number>();
  readonly submitApplication = output<void>();
}
