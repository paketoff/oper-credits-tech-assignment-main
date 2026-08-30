import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

/**
 * The show/hide control that sits inside a password field.
 *
 * Presentation only, and deliberately dumb: it does not own the input, the
 * form control, or even the visibility state — it takes the state and emits an
 * intent. `shared/` carries no business logic and imports no domain
 * (`ARC-025`), and the two auth pages differ enough in their error handling
 * that wrapping their inputs would have cost more than it saved.
 */
@Component({
  selector: 'app-password-toggle',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <button
      type="button"
      (click)="toggled.emit()"
      [attr.aria-label]="visible() ? 'Hide password' : 'Show password'"
      [attr.aria-pressed]="visible()"
      class="text-muted hover:text-ink absolute top-1/2 right-2 flex size-8 -translate-y-1/2 cursor-pointer items-center justify-center rounded-full transition-colors"
    >
      @if (visible()) {
        <svg viewBox="0 0 20 20" width="18" height="18" fill="currentColor" aria-hidden="true">
          <path
            d="M2.3 2.3a1 1 0 0 1 1.4 0l14 14a1 1 0 0 1-1.4 1.4l-2.2-2.2A9 9 0 0 1 10 16c-4 0-7.4-2.5-9-6a12 12 0 0 1 3.6-4.3L2.3 3.7a1 1 0 0 1 0-1.4Zm4.1 5.5A4 4 0 0 0 10 14a4 4 0 0 0 1.8-.4l-1.5-1.6a2 2 0 0 1-2.3-2.3L6.4 7.8ZM10 4c4 0 7.4 2.5 9 6a12 12 0 0 1-2.4 3.3l-2.6-2.6A4 4 0 0 0 9.3 6.1L7.6 4.4A9 9 0 0 1 10 4Z"
          />
        </svg>
      } @else {
        <svg viewBox="0 0 20 20" width="18" height="18" fill="currentColor" aria-hidden="true">
          <path
            d="M10 4c-4 0-7.4 2.5-9 6 1.6 3.5 5 6 9 6s7.4-2.5 9-6c-1.6-3.5-5-6-9-6Zm0 10a4 4 0 1 1 0-8 4 4 0 0 1 0 8Zm0-2a2 2 0 1 0 0-4 2 2 0 0 0 0 4Z"
          />
        </svg>
      }
    </button>
  `,
})
export class PasswordToggleComponent {
  readonly visible = input(false);
  readonly toggled = output<void>();
}
