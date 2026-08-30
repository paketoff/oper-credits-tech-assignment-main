import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { switchMap } from 'rxjs';

import { ApiError } from '../../../core/error-codes';
import { ApplicationService } from '../../application/application.service';
import { SimulationService } from '../../simulation/simulation.service';
import { PasswordToggleComponent } from '../../../shared/password-toggle.component';
import { AuthBrandingPanelComponent } from '../components/auth-branding-panel.component';
import { AuthService } from '../auth.service';

interface SignupFormControls {
  email: FormControl<string>;
  password: FormControl<string>;
}

/**
 * Two-column split layout, `max-w-[64rem]` (`UI-054`): form left, branding
 * panel right, single column on mobile. Sends the anonymous simulation id
 * along if one exists (`AUTH-049`, `UX-027`), then creates the draft it
 * seeds — signup only claims, it does not create the application itself
 * (`2-architecture.md` §5.1).
 */
@Component({
  selector: 'app-signup-page',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ReactiveFormsModule, RouterLink, AuthBrandingPanelComponent, PasswordToggleComponent],
  templateUrl: './signup-page.component.html',
})
export class SignupPageComponent {
  private readonly authService = inject(AuthService);
  private readonly simulationService = inject(SimulationService);
  private readonly applicationService = inject(ApplicationService);
  private readonly router = inject(Router);

  readonly form = new FormGroup<SignupFormControls>({
    email: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    password: new FormControl('', {
      nonNullable: true,
      // AUTH-010: minimum 10 characters, nothing else — composition rules
      // reduce entropy in practice.
      validators: [Validators.required, Validators.minLength(10)],
    }),
  });

  protected readonly passwordVisible = signal(false);
  protected readonly submitting = signal(false);
  /** A field-less error only — a field-level one is set on its own control (UX-024). */
  protected readonly formError = signal<string | null>(null);

  protected togglePassword(): void {
    this.passwordVisible.update((visible) => !visible);
  }

  protected submit(): void {
    if (this.form.invalid || this.submitting()) {
      return;
    }
    this.submitting.set(true);
    this.formError.set(null);

    const { email, password } = this.form.getRawValue();
    const simulationId = this.simulationService.lastId();

    this.authService
      .signup({ email, password, simulation_id: simulationId })
      .pipe(
        switchMap((response) =>
          this.applicationService.create({
            simulation_id: response.claimed_simulation_id,
          }),
        ),
      )
      .subscribe({
        next: (application) => {
          // The id has done its job and can never be claimed twice (DOM-027);
          // keeping it would offer a stale simulation to the next signup in
          // this tab.
          this.simulationService.forget();
          void this.router.navigate(['/applications', application.id]);
        },
        error: (error: unknown) => {
          this.submitting.set(false);
          this.applyError(error);
        },
      });
  }

  /** Places a field-level error beside its control; anything else above the form (never a toast). */
  private applyError(error: unknown): void {
    if (!(error instanceof HttpErrorResponse)) {
      this.formError.set('Something went wrong. Please try again.');
      return;
    }
    const body = error.error as ApiError | undefined;
    if (body?.field && body.field in this.form.controls) {
      this.form.controls[body.field as keyof SignupFormControls].setErrors({
        server: body.message,
      });
      return;
    }
    this.formError.set(body?.message ?? 'Something went wrong. Please try again.');
  }
}
