import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';

import { LogoMarkComponent } from '../theme/logo-mark.component';
import { ThemeToggleComponent } from '../theme/theme-toggle.component';
import { User } from '../auth-state.service';

/**
 * The one dark surface in the application (`UI-055`): a 56px near-black band,
 * the mark, product name and a `Calculator` nav link on the left (visible in
 * every mode, including `minimal` — it's a nav link, not an account control),
 * the theme toggle (`UX-064`, also visible in every mode — a global
 * preference, not an account control) and account state on the right.
 *
 * Dumb by construction — inputs in, one output out, nothing injected — even
 * though it lives in `core/shell/` rather than a domain's `components/`
 * (`ARC-022`'s letter is about domain folders; its reasoning applies here
 * just as well).
 */
@Component({
  selector: 'app-header',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LogoMarkComponent, ThemeToggleComponent],
  template: `
    <header class="bg-ink-fixed flex h-14 items-center justify-between px-4 md:px-8">
      <div class="flex items-center gap-6">
        <a routerLink="/" class="text-surface-fixed flex items-center gap-2">
          <app-logo-mark tone="inverted" [size]="24" />
          <span class="font-display text-h3 tracking-tight-1 font-semibold">Borrower Portal</span>
        </a>
        <a
          routerLink="/calculator"
          class="text-body-sm text-surface-fixed/80 hover:text-surface-fixed hidden font-semibold transition-colors sm:inline"
        >
          Calculator
        </a>
      </div>

      <div class="flex items-center gap-3">
        <app-theme-toggle />
        @if (!minimal()) {
          @if (user(); as currentUser) {
            <a
              routerLink="/applications"
              class="rounded-control text-body-sm text-surface-fixed px-3 py-1.5 font-semibold transition-colors hover:bg-white/10"
            >
              My applications
            </a>
            <span class="text-body-sm text-surface-fixed/80">{{ currentUser.email }}</span>
            <button
              type="button"
              (click)="logout.emit()"
              class="rounded-control text-body-sm text-surface-fixed px-3 py-1.5 font-semibold transition-colors hover:bg-white/10"
            >
              Log out
            </button>
          } @else {
            <a
              routerLink="/login"
              class="rounded-control text-body-sm text-surface-fixed px-3 py-1.5 font-semibold transition-colors hover:bg-white/10"
            >
              Log in
            </a>
            <a
              routerLink="/signup"
              class="rounded-control bg-accent hover:bg-accent-hover text-body-sm px-3 py-1.5 font-semibold text-white transition-colors"
            >
              Sign up
            </a>
          }
        }
      </div>
    </header>
  `,
})
export class AppHeaderComponent {
  readonly user = input<User | null>(null);
  /** True on the auth screens: no account menu, there is no account yet (§1). */
  readonly minimal = input(false);
  readonly logout = output<void>();
}
