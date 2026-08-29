import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { filter, map, startWith } from 'rxjs';

import { AppHeaderComponent } from './core/shell/app-header.component';
import { AuthState } from './core/auth-state.service';
import { AuthService } from './domains/auth/auth.service';

const AUTH_ROUTES = ['/login', '/signup'];

/**
 * The root shell: the header from `UI-055` on every route, reduced to the
 * minimal top bar from §1 of the plan on the two auth screens. One component
 * owns this decision so no page has to know about the header at all.
 */
@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, AppHeaderComponent],
  templateUrl: './app.html',
})
export class App {
  private readonly router = inject(Router);
  private readonly authState = inject(AuthState);
  private readonly authService = inject(AuthService);

  protected readonly user = this.authState.currentUser;

  private readonly url = toSignal(
    this.router.events.pipe(
      filter((event): event is NavigationEnd => event instanceof NavigationEnd),
      map((event) => event.urlAfterRedirects),
      startWith(this.router.url),
    ),
    { initialValue: this.router.url },
  );

  protected readonly minimalHeader = computed(() =>
    AUTH_ROUTES.some((route) => this.url().startsWith(route)),
  );

  protected logout(): void {
    // AUTH-028: succeeds whether or not a session existed; AuthService.logout
    // clears the local signal once the endpoint responds.
    this.authService.logout().subscribe(() => {
      void this.router.navigate(['/login']);
    });
  }
}
