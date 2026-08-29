import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

type LogoTone = 'accent' | 'inverted';

/**
 * The application's mark: a house with a key, standing in for the closing day
 * this whole portal is built around. One placeholder mark, one accent colour
 * (UI-007) — `tone` swaps which of the two elements reads light versus dark,
 * because a plain `currentColor` inherit would make the keyhole invisible
 * against the header's dark band (`UI-055`) once the house itself turns white.
 */
@Component({
  selector: 'app-logo-mark',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg
      [attr.width]="size()"
      [attr.height]="size()"
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
    >
      <path [class]="houseClass()" d="M16 5 4 14v13h8v-8h8v8h8V14L16 5Z" fill="currentColor" />
      <circle [class]="keyholeClass()" cx="16" cy="16.5" r="2.4" fill="currentColor" />
      <path
        [class]="keyholeClass()"
        d="M16 18.9v3.4"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
      />
    </svg>
  `,
})
export class LogoMarkComponent {
  readonly size = input(28);
  readonly tone = input<LogoTone>('accent');

  protected readonly houseClass = computed(() =>
    this.tone() === 'inverted' ? 'text-surface' : 'text-accent',
  );
  protected readonly keyholeClass = computed(() =>
    this.tone() === 'inverted' ? 'text-ink' : 'text-surface',
  );
}
