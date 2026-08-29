import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { LogoMarkComponent } from '../theme/logo-mark.component';
import { User } from '../auth-state.service';

/**
 * The one dark surface in the application (`UI-055`): a 56px near-black band,
 * the mark and product name on the left, account state on the right.
 *
 * Dumb by construction — inputs in, one output out, nothing injected — even
 * though it lives in `core/shell/` rather than a domain's `components/`
 * (`ARC-022`'s letter is about domain folders; its reasoning applies here
 * just as well).
 */
@Component({
  selector: 'app-header',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LogoMarkComponent],
  template: `
    <header class="bg-ink flex h-14 items-center justify-between px-4 md:px-8">
      <a routerLink="/" class="text-surface flex items-center gap-2">
        <app-logo-mark tone="inverted" [size]="24" />
        <span class="font-display text-h3 tracking-tight-1 font-semibold">Borrower Portal</span>
      </a>

      @if (!minimal()) {
        @if (user(); as currentUser) {
          <div class="flex items-center gap-3">
            <span class="text-body-sm text-surface/80">{{ currentUser.email }}</span>
            <button
              type="button"
              (click)="logout.emit()"
              class="rounded-control text-body-sm text-surface px-3 py-1.5 font-semibold transition-colors hover:bg-white/10"
            >
              Log out
            </button>
          </div>
        } @else {
          <a
            routerLink="/login"
            class="rounded-control text-body-sm text-surface px-3 py-1.5 font-semibold transition-colors hover:bg-white/10"
          >
            Log in
          </a>
        }
      }
    </header>
  `,
})
export class AppHeaderComponent {
  readonly user = input<User | null>(null);
  /** True on the auth screens: no account menu, there is no account yet (§1). */
  readonly minimal = input(false);
  readonly logout = output<void>();
}
