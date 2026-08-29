import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

import { MoneyPipe } from '../../../shared/money.pipe';
import { PercentPipe } from '../../../shared/percent.pipe';
import { Simulation } from '../simulation.models';

/**
 * The result panel. Dumb (`ARC-022`): the page decides when a new value
 * arrives, this component only ever renders whatever it was last given.
 *
 * `loading` dims the panel slightly rather than hiding it — the previous
 * result must stay visible while a new one computes (`UX-013`, `UI-047` –
 * `UI-051`).
 */
@Component({
  selector: 'app-simulation-result',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [MoneyPipe, PercentPipe],
  templateUrl: './simulation-result.component.html',
})
export class SimulationResultComponent {
  readonly result = input<Simulation | null>(null);
  readonly loading = input(false);

  protected readonly breakdownOpen = signal(false);

  protected readonly aboveNorm = computed(() => this.result()?.above_supervisory_norm ?? false);

  protected toggleBreakdown(): void {
    this.breakdownOpen.update((open) => !open);
  }
}
