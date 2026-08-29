import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ApplicationStatus } from '../../../core/models';
import { MoneyPipe } from '../../../shared/money.pipe';
import { ApplicationSummary } from '../application.models';
import { ApplicationService } from '../application.service';

interface StatusChip {
  label: string;
  classes: string;
}

const STATUS_CHIPS: Record<ApplicationStatus, StatusChip> = {
  DRAFT: { label: 'Draft', classes: 'bg-surface-3 text-muted' },
  SUBMITTED: { label: 'Submitted', classes: 'bg-signal-soft text-ink-fixed' },
  DOCUMENTS_PENDING: { label: 'Documents pending', classes: 'bg-signal-soft text-ink-fixed' },
  DOCUMENTS_COMPLETE: { label: 'Documents complete', classes: 'bg-success-soft text-success' },
  UNDER_REVIEW: { label: 'Under review', classes: 'bg-signal-soft text-ink-fixed' },
  OFFER_ISSUED: { label: 'Offer issued', classes: 'bg-success-soft text-success' },
  WITHDRAWN: { label: 'Withdrawn', classes: 'bg-danger-soft text-danger-fixed' },
};

/**
 * "My applications" (`API-029` – `API-031`): the backend has always listed a
 * borrower's own applications, but nothing in the frontend read it until
 * this ticket — a returning, logged-in borrower had no way back to their
 * application except a guard redirect or a remembered URL.
 */
@Component({
  selector: 'app-applications-list-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, MoneyPipe],
  templateUrl: './applications-list.component.html',
})
export class ApplicationsListComponent {
  private readonly applicationService = inject(ApplicationService);

  protected readonly items = signal<ApplicationSummary[] | null>(null);
  protected readonly statusChips = STATUS_CHIPS;

  constructor() {
    this.applicationService.list().subscribe((result) => this.items.set(result.items));
  }
}
