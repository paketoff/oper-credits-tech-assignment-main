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
  /** Whether what the borrower confirmed equals what the document said. */
  matches: boolean;
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
   * Every figure a document offered — the ones still open *and* the ones
   * already confirmed.
   *
   * This used to drop a row the moment it agreed with what was saved, which
   * meant the evidence disappeared exactly when it started being worth
   * something: a borrower who accepted €2 500 from their payslip and saved it
   * had no way left to see that the assessment was running on the figure the
   * document actually stated. Agreement is the thing being demonstrated, so it
   * is shown rather than hidden.
   */
  /** True once every figure a document offered has been confirmed unchanged. */
  protected readonly allReconciled = computed(
    () => this.rows().length > 0 && this.rows().every((row) => row.matches),
  );

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
    if (proposed === null) {
      return;
    }
    rows.push({
      field,
      label,
      proposed,
      current,
      source: proposal.source,
      matches: proposed === current,
    });
  }
}
