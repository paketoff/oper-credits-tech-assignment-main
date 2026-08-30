import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

import { MoneyPipe } from '../../../shared/money.pipe';
import { DocumentProposal } from '../../documents/documents.models';

/** One figure a document suggested, next to what the borrower currently has. */
export interface ProposalRow {
  field: 'net_monthly_income' | 'existing_credit_monthly';
  label: string;
  proposed: string;
  current: string | null;
  source: string;
}

/**
 * The reconciliation prompt (`T59`) — the moment this whole design exists for.
 *
 * A document read a figure; the borrower is shown both and decides. Never
 * silent, never automatic: accepting is a click, and doing nothing keeps what
 * they typed. This is what makes "the human is in the loop" visible rather than
 * asserted, and it is why a misread number can never reach an affordability
 * band (`DOM-030`).
 *
 * Dumb (`ARC-022`): rows in, one output out, nothing injected.
 */
@Component({
  selector: 'app-proposal-prompt',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MoneyPipe],
  templateUrl: './proposal-prompt.component.html',
})
export class ProposalPromptComponent {
  readonly proposals = input<DocumentProposal[]>([]);
  readonly currentIncome = input<string | null>(null);
  readonly currentCredit = input<string | null>(null);

  readonly accept = output<ProposalRow>();

  /**
   * Only figures that actually disagree with what is already confirmed.
   * Proposing what the borrower already has is noise, not help.
   */
  protected readonly rows = computed<ProposalRow[]>(() => {
    const rows: ProposalRow[] = [];
    for (const proposal of this.proposals()) {
      this.collect(
        rows,
        proposal,
        'net_monthly_income',
        'Net monthly income',
        this.currentIncome(),
      );
      this.collect(
        rows,
        proposal,
        'existing_credit_monthly',
        'Existing monthly credit',
        this.currentCredit(),
      );
    }
    return rows;
  });

  private collect(
    rows: ProposalRow[],
    proposal: DocumentProposal,
    field: ProposalRow['field'],
    label: string,
    current: string | null,
  ): void {
    const proposed = proposal[field];
    if (proposed === null || proposed === current) {
      return;
    }
    rows.push({ field, label, proposed, current, source: proposal.source });
  }
}
