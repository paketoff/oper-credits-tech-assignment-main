import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { LogoMarkComponent } from '../../../core/theme/logo-mark.component';

interface HowItWorksStep {
  step: number;
  title: string;
  body: string;
}

interface Benefit {
  title: string;
  body: string;
}

const STEPS: HowItWorksStep[] = [
  {
    step: 1,
    title: 'Simulate',
    body: 'See your monthly payment and the cash you need on the day, computed live as you type.',
  },
  {
    step: 2,
    title: 'Sign up & apply',
    body: 'Create an account and your simulation carries straight into a prefilled application.',
  },
  {
    step: 3,
    title: 'Upload documents',
    body: 'A checklist tells you exactly what is required and why — nothing left to guess.',
  },
];

const BENEFITS: Benefit[] = [
  {
    title: 'Belgian rules, built in',
    body: 'Regional purchase tax and quotiteit norms, not a generic calculator.',
  },
  {
    title: 'The real number',
    body: 'Cash needed on the day, shown with the same weight as the monthly payment.',
  },
  {
    title: 'Secure by design',
    body: 'Documents are re-checked on every request — never served as static files.',
  },
  {
    title: 'No dashboard maze',
    body: 'Sign up and land directly on your own prefilled application.',
  },
];

/**
 * The public entry point (`UI-069`) — an anonymous visitor's first screen.
 * The simulator itself stays public and computed-on-load exactly as `UX-009`
 * requires; it just isn't the very first thing reached anymore.
 *
 * No service, no HTTP (`ARC-021`) — a static marketing page has nothing to
 * inject.
 */
@Component({
  selector: 'app-home-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, LogoMarkComponent],
  templateUrl: './home-page.component.html',
})
export class HomePageComponent {
  protected readonly steps = STEPS;
  protected readonly benefits = BENEFITS;
}
