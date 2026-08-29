import { Routes } from '@angular/router';

import { authGuard } from './domains/auth/auth.guard';
import { LoginPageComponent } from './domains/auth/pages/login-page.component';
import { SignupPageComponent } from './domains/auth/pages/signup-page.component';
import { ApplicationWizardComponent } from './domains/application/pages/application-wizard.component';
import { ApplicationsListComponent } from './domains/application/pages/applications-list.component';
import { HomePageComponent } from './domains/home/pages/home-page.component';
import { SimulatorPageComponent } from './domains/simulation/pages/simulator-page.component';

/**
 * Root is the public marketing home page (`UI-069`) — an anonymous visitor's
 * first screen. The simulator moved to `/calculator`; it is still public and
 * still computed-and-prefilled on load exactly as `UX-009` requires, it just
 * is not the very first thing reached anymore (T46).
 */
export const routes: Routes = [
  { path: '', component: HomePageComponent },
  { path: 'calculator', component: SimulatorPageComponent },
  { path: 'signup', component: SignupPageComponent },
  { path: 'login', component: LoginPageComponent },
  { path: 'applications', component: ApplicationsListComponent, canActivate: [authGuard] },
  {
    path: 'applications/:id',
    component: ApplicationWizardComponent,
    canActivate: [authGuard],
  },
];
