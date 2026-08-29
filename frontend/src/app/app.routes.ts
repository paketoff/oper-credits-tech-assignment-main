import { Routes } from '@angular/router';

import { SimulatorPageComponent } from './domains/simulation/pages/simulator-page.component';

/**
 * Filled in as each domain's page component lands — T27 (simulator, the
 * root), T28 (signup, login, the guard), T29 (the wizard). Simulator sits at
 * the root because it is what the app opens with, computed and prefilled,
 * before any account exists (`UX-009`).
 */
export const routes: Routes = [{ path: '', component: SimulatorPageComponent }];
