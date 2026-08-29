import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { LogoMarkComponent } from '../../../core/theme/logo-mark.component';

interface TrustPoint {
  text: string;
}

const TRUST_POINTS: TrustPoint[] = [
  { text: 'Belgian purchase tax and quotiteit norms, built in' },
  { text: 'Your application picks up exactly where the simulation left off' },
  { text: 'Documents are re-checked on every request, never served as static files' },
];

/**
 * The right-hand panel of the Google/Stripe-style split auth layout
 * (`UI-054`) — shared by signup and login so the branding markup exists
 * once. Dumb (`ARC-022`): a `tagline` input, nothing injected.
 */
@Component({
  selector: 'app-auth-branding-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [LogoMarkComponent],
  templateUrl: './auth-branding-panel.component.html',
})
export class AuthBrandingPanelComponent {
  readonly tagline = input('Belgian mortgages, simplified.');

  protected readonly trustPoints = TRUST_POINTS;
}
