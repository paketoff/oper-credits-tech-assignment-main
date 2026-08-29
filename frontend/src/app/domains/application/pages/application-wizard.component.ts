import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Step, StepItem, StepList, StepPanel, StepPanels, Stepper } from 'primeng/stepper';
import { switchMap, tap } from 'rxjs';

import { EmploymentType, PropertyType, Region } from '../../../core/models';
import { Simulation } from '../../simulation/simulation.models';
import { SimulationService } from '../../simulation/simulation.service';
import { Application } from '../application.models';
import { ApplicationService } from '../application.service';
import { BorrowerFormControls, BorrowerStepComponent } from '../components/borrower-step.component';
import { PropertyFormControls, PropertyStepComponent } from '../components/property-step.component';
import { ReviewStepComponent } from '../components/review-step.component';

const TOTAL_STEPS = 4;

/**
 * Four steps, `p-stepper` (`UX-029`, `UI-036`). Only the current step
 * validates (`UX-032`); the draft saves server-side after step 1 (`UX-033`),
 * so a refresh mid-wizard loses nothing past that point.
 */
@Component({
  selector: 'app-application-wizard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    Stepper,
    StepList,
    StepItem,
    StepPanels,
    StepPanel,
    Step,
    BorrowerStepComponent,
    PropertyStepComponent,
    ReviewStepComponent,
  ],
  templateUrl: './application-wizard.component.html',
})
export class ApplicationWizardComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly applicationService = inject(ApplicationService);
  private readonly simulationService = inject(SimulationService);

  private readonly applicationId = this.route.snapshot.paramMap.get('id') ?? '';

  protected readonly activeStep = signal(1);
  protected readonly application = signal<Application | null>(null);
  protected readonly simulation = signal<Simulation | null>(null);
  protected readonly submitting = signal(false);

  // VAL-011: at least one borrower, each requiring full_name, date_of_birth,
  // employment_type. Only this step's own fields are validated (UX-032) —
  // the property form below carries none of these constraints.
  protected readonly borrowerForm = new FormGroup<BorrowerFormControls>({
    full_name: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    date_of_birth: new FormControl('', { nonNullable: true, validators: [Validators.required] }),
    employment_type: new FormControl<EmploymentType>('EMPLOYEE', { nonNullable: true }),
    monthly_net_income: new FormControl<number | null>(null),
    has_existing_credit: new FormControl(false, { nonNullable: true }),
  });

  protected readonly propertyForm = new FormGroup<PropertyFormControls>({
    region: new FormControl<Region>('FLANDERS', { nonNullable: true }),
    is_first_home: new FormControl(true, { nonNullable: true }),
    property_type: new FormControl<PropertyType>('EXISTING', { nonNullable: true }),
    purchase_price: new FormControl(300_000, {
      nonNullable: true,
      validators: [Validators.required, Validators.min(10_000)],
    }),
  });

  constructor() {
    this.applicationService
      .get(this.applicationId)
      .pipe(
        tap((application) => this.hydrate(application)),
        switchMap((application) =>
          application.simulation_id
            ? this.simulationService.get(application.simulation_id)
            : [null],
        ),
      )
      .subscribe((simulation) => this.simulation.set(simulation));
  }

  protected goToStep(step: number): void {
    this.activeStep.set(step);
  }

  protected next(): void {
    if (this.activeStep() === 1) {
      this.saveBorrower();
    } else if (this.activeStep() === 2) {
      this.saveProperty();
    } else {
      this.activeStep.set(Math.min(this.activeStep() + 1, TOTAL_STEPS));
    }
  }

  protected back(): void {
    this.activeStep.set(Math.max(this.activeStep() - 1, 1));
  }

  protected submit(): void {
    if (this.submitting()) {
      return;
    }
    this.submitting.set(true);
    this.applicationService.submit(this.applicationId).subscribe({
      next: (application) => {
        this.application.set(application);
        this.submitting.set(false);
      },
      error: () => {
        this.submitting.set(false);
      },
    });
  }

  private saveBorrower(): void {
    if (this.borrowerForm.invalid) {
      this.borrowerForm.markAllAsTouched();
      return;
    }
    const raw = this.borrowerForm.getRawValue();
    this.applicationService
      .patch(this.applicationId, {
        borrowers: [
          {
            ...raw,
            monthly_net_income:
              raw.monthly_net_income === null ? null : raw.monthly_net_income.toFixed(2),
          },
        ],
      })
      .subscribe((application) => {
        this.application.set(application);
        this.activeStep.set(2);
      });
  }

  private saveProperty(): void {
    if (this.propertyForm.invalid) {
      this.propertyForm.markAllAsTouched();
      return;
    }
    const raw = this.propertyForm.getRawValue();
    this.applicationService
      .patch(this.applicationId, {
        property: { ...raw, purchase_price: raw.purchase_price.toFixed(2) },
      })
      .subscribe((application) => {
        this.application.set(application);
        this.activeStep.set(3);
      });
  }

  private hydrate(application: Application): void {
    this.application.set(application);
    const [borrower] = application.borrowers;
    if (borrower) {
      this.borrowerForm.patchValue({
        full_name: borrower.full_name,
        date_of_birth: borrower.date_of_birth,
        employment_type: borrower.employment_type,
        monthly_net_income: borrower.monthly_net_income
          ? Number(borrower.monthly_net_income)
          : null,
        has_existing_credit: borrower.has_existing_credit,
      });
    }
    if (application.property) {
      this.propertyForm.patchValue({
        region: application.property.region,
        is_first_home: application.property.is_first_home,
        property_type: application.property.property_type ?? 'EXISTING',
        purchase_price: Number(application.property.purchase_price),
      });
    }
  }
}
