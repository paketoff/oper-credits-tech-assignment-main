import { provideHttpClient, withInterceptors } from '@angular/common/http';
import {
  ApplicationConfig,
  inject,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import { providePrimeNG } from 'primeng/config';
import { firstValueFrom } from 'rxjs';

import { routes } from './app.routes';
import { authInterceptor } from './core/auth.interceptor';
import { errorInterceptor } from './core/error.interceptor';
import { OperPreset } from './core/theme/oper-preset';
import { AuthService } from './domains/auth/auth.service';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor, errorInterceptor])),
    // AUTH-046: auth state comes from GET /api/auth/me on application boot.
    // Blocking bootstrap on it — rather than firing it from a component —
    // means the auth guard never runs before the session is known either way.
    provideAppInitializer(() => {
      const authService = inject(AuthService);
      return firstValueFrom(authService.resolveSession());
    }),
    // UI-038: layer order matters, or PrimeNG's styles beat Tailwind's
    // utilities.
    providePrimeNG({
      theme: {
        preset: OperPreset,
        options: {
          darkModeSelector: false,
          cssLayer: { name: 'primeng', order: 'theme, base, primeng, components, utilities' },
        },
      },
    }),
  ],
};
