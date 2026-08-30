import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { MoneyPipe } from '../../../shared/money.pipe';
import { ApplicationSummary } from '../application.models';
import { STATUS_CHIPS } from '../status-chip';
import { ApplicationService } from '../application.service';

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
