import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { ApiError } from '../../../core/error-codes';
import { AuthBrandingPanelComponent } from '../components/auth-branding-panel.component';
import { AuthService } from '../auth.service';

interface LoginFormControls {
  email: FormControl<string>;
  password: FormControl<string>;
}

/**
 * Two-column split layout, same shape as signup (`UI-054`). Redirects to
 * whatever URL the guard preserved (`AUTH-048`); with no preserved URL —
 * arriving here without being redirected — a returning borrower lands on
 * their own applications, not the marketing home page.
 */
@Component({
  selector: 'app-login-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, AuthBrandingPanelComponent],
  templateUrl: './login-page.component.html',
})
export class LoginPageComponent {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);

  readonly form = new FormGroup<LoginFormControls>({
    email: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    password: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
  });

  protected readonly submitting = signal(false);
  protected readonly formError = signal<string | null>(null);

  protected submit(): void {
    if (this.form.invalid || this.submitting()) {
      return;
    }
    this.submitting.set(true);
    this.formError.set(null);

    this.authService.login(this.form.getRawValue()).subscribe({
      next: () => {
        const redirect = this.route.snapshot.queryParamMap.get('redirect') ?? '/applications';
        void this.router.navigateByUrl(redirect);
      },
      error: (error: unknown) => {
        this.submitting.set(false);
        this.applyError(error);
      },
    });
  }

  private applyError(error: unknown): void {
    if (!(error instanceof HttpErrorResponse)) {
      this.formError.set('Something went wrong. Please try again.');
      return;
    }
    const body = error.error as ApiError | undefined;
    // AUTH-025: wrong email and wrong password are identical — INVALID_CREDENTIALS
    // never names a field, so it always renders here rather than on a control.
    this.formError.set(body?.message ?? 'Something went wrong. Please try again.');
  }
}
