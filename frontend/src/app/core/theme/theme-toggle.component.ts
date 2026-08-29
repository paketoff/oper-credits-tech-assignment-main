import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { ThemeService } from './theme.service';

/**
 * Sun/moon toggle (`UX-064`). Injects `ThemeService` directly rather than
 * taking an `@input`/`@output` pair — a `core/shell`-level control, the same
 * documented exception `AppHeaderComponent` already uses, not a domain
 * component bound by `ARC-022`'s domain-only rule.
 */
@Component({
  selector: 'app-theme-toggle',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <button
      type="button"
      (click)="theme.toggle()"
      [attr.aria-label]="theme.isDark() ? 'Switch to light theme' : 'Switch to dark theme'"
      class="text-surface-fixed/80 hover:text-surface-fixed flex size-8 items-center justify-center rounded-full transition-colors hover:bg-white/10"
    >
      @if (theme.isDark()) {
        <svg viewBox="0 0 20 20" width="18" height="18" fill="currentColor" aria-hidden="true">
          <path
            d="M10 2a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0V3a1 1 0 0 1 1-1Zm0 13a1 1 0 0 1 1 1v1a1 1 0 1 1-2 0v-1a1 1 0 0 1 1-1ZM3 10a1 1 0 0 1 1-1h1a1 1 0 1 1 0 2H4a1 1 0 0 1-1-1Zm12 0a1 1 0 0 1 1-1h1a1 1 0 1 1 0 2h-1a1 1 0 0 1-1-1ZM5.05 5.05a1 1 0 0 1 1.415 0l.707.707a1 1 0 1 1-1.414 1.415l-.708-.708a1 1 0 0 1 0-1.414Zm8.485 8.485a1 1 0 0 1 1.415 0l.707.707a1 1 0 0 1-1.414 1.415l-.708-.708a1 1 0 0 1 0-1.414ZM14.95 5.05a1 1 0 0 1 0 1.415l-.707.707a1 1 0 1 1-1.415-1.414l.708-.708a1 1 0 0 1 1.414 0ZM6.465 13.535a1 1 0 0 1 0 1.415l-.707.707a1 1 0 0 1-1.415-1.414l.708-.708a1 1 0 0 1 1.414 0ZM10 6a4 4 0 1 1 0 8 4 4 0 0 1 0-8Z"
          />
        </svg>
      } @else {
        <svg viewBox="0 0 20 20" width="18" height="18" fill="currentColor" aria-hidden="true">
          <path d="M17.293 13.293A8 8 0 0 1 6.707 2.707a8.001 8.001 0 1 0 10.586 10.586Z" />
        </svg>
      }
    </button>
  `,
})
export class ThemeToggleComponent {
  protected readonly theme = inject(ThemeService);
}
