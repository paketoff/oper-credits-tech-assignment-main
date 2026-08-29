import { Routes } from '@angular/router';

import { LoginPageComponent } from './domains/auth/pages/login-page.component';
import { SignupPageComponent } from './domains/auth/pages/signup-page.component';
import { SimulatorPageComponent } from './domains/simulation/pages/simulator-page.component';

/**
 * Filled in as each domain's page component lands — T27 (simulator, the
 * root), T28 (signup, login), T29 (the wizard, `applications/:id`, behind
 * `domains/auth/auth.guard.ts`). Simulator sits at the root because it is
 * what the app opens with, computed and prefilled, before any account exists
 * (`UX-009`). The guard itself is built and tested in T28 but only wired
 * here once T29 adds the route it protects.
 */
export const routes: Routes = [
  { path: '', component: SimulatorPageComponent },
  { path: 'signup', component: SignupPageComponent },
  { path: 'login', component: LoginPageComponent },
];
