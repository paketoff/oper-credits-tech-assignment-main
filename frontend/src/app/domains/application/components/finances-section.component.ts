import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { InputNumber } from 'primeng/inputnumber';

import { MoneyPipe } from '../../../shared/money.pipe';
import { PercentPipe } from '../../../shared/percent.pipe';
import { AffordabilityBand, Financials, FinancialsRequest } from '../application.models';

export interface FinancesFormControls {
  net_monthly_income: FormControl<number | null>;
  existing_credit_monthly: FormControl<number | null>;
  dependants: FormControl<number>;
}

interface BandCopy {
  label: string;
  classes: string;
  body: string;
}

/**
 * How each band reads to the borrower. Informational throughout: not one of
 * these says approved or rejected, because the assessment is a band and never
 * a decision (`SIM-028`) — the same treatment the above-norm quotiteit chip
 * gets, and for the same reason.
 */
const BAND_COPY: Record<AffordabilityBand, BandCopy> = {
  COMFORTABLE: {
    label: 'Comfortable',
    classes: 'bg-success-soft text-success',
    body: 'Your income share and what you keep each month both sit inside the norms lenders typically apply.',
  },
  TIGHT: {
    label: 'Tight',
    classes: 'bg-signal-soft text-ink-fixed',
    body: 'This is inside what lenders typically accept, but with little room. A larger own contribution or a longer term would ease it.',
  },
  OUTSIDE_TYPICAL_NORMS: {
    label: 'Outside typical norms',
    classes: 'bg-signal-soft text-ink-fixed',
    body: 'This sits outside the norms most lenders apply. It is not a refusal — lenders assess individually — but expect questions.',
  },
  INSUFFICIENT_DATA: {
    label: 'Not enough information',
    classes: 'bg-surface-3 text-muted',
    body: 'Add your net monthly income to see how this loan sits against the usual norms.',
  },
};

/**
 * The finances section: what the borrower earns and already owes, and how the
 * loan sits against it (`0-business-logic.md` §21).
 *
 * Dumb (`ARC-022`): the page owns the form group and the HTTP call. This is
 * the manual-entry base case — extraction, when it exists, pre-fills exactly
 * these fields and changes nothing else, because a proposal is only ever a
 * proposal until it is confirmed here (`DOM-030`).
 */
@Component({
  selector: 'app-finances-section',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, InputNumber, MoneyPipe, PercentPipe],
  templateUrl: './finances-section.component.html',
})
export class FinancesSectionComponent {
  readonly form = input.required<FormGroup<FinancesFormControls>>();
  readonly financials = input<Financials | null>(null);
  readonly saving = input(false);
  /**
   * The simulation the borrower has in this browser session, when the
   * application has none of its own. Null hides the offer and leaves only the
   * explanation — there is nothing to attach.
   */
  readonly attachableSimulationId = input<string | null>(null);
  readonly attaching = input(false);

  readonly save = output<FinancialsRequest>();
  readonly attachSimulation = output<string>();

  protected readonly bandCopy = BAND_COPY;

  protected onSubmit(): void {
    const raw = this.form().getRawValue();
    this.save.emit({
      // Money crosses the wire as a string and is only ever parsed for display
      // (`CQ-014`, `CQ-027`): the number here is the input control's, and this
      // is where it stops being one.
      net_monthly_income:
        raw.net_monthly_income === null ? null : raw.net_monthly_income.toFixed(2),
      existing_credit_monthly:
        raw.existing_credit_monthly === null ? null : raw.existing_credit_monthly.toFixed(2),
      dependants: raw.dependants,
    });
  }
}
