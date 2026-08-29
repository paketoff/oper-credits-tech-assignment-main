import { Routes } from '@angular/router';

import { authGuard } from './domains/auth/auth.guard';
import { LoginPageComponent } from './domains/auth/pages/login-page.component';
import { SignupPageComponent } from './domains/auth/pages/signup-page.component';
import { ApplicationWizardComponent } from './domains/application/pages/application-wizard.component';
import { SimulatorPageComponent } from './domains/simulation/pages/simulator-page.component';

/**
 * Simulator sits at the root because it is what the app opens with, computed
 * and prefilled, before any account exists (`UX-009`). The wizard is behind
 * `authGuard`, built and tested at T28 but wired here now that T29 gives it
 * something to protect.
 */
export const routes: Routes = [
  { path: '', component: SimulatorPageComponent },
  { path: 'signup', component: SignupPageComponent },
  { path: 'login', component: LoginPageComponent },
  {
    path: 'applications/:id',
    component: ApplicationWizardComponent,
    canActivate: [authGuard],
  },
];
