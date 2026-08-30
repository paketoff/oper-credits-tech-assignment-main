import { HttpErrorResponse } from '@angular/common/http';
import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormControl, FormGroup, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { Step, StepItem, StepList, StepPanel, StepPanels, Stepper } from 'primeng/stepper';
import { switchMap, tap } from 'rxjs';

import { ApiError } from '../../../core/error-codes';
import { EmploymentType, PropertyType, Region } from '../../../core/models';
import {
  ChecklistComponent,
  DocumentRemoval,
  FileSelection,
  RowStatus,
} from '../../documents/components/checklist.component';
import { Checklist, DocumentProposal } from '../../documents/documents.models';
import { DocumentsService } from '../../documents/documents.service';
import { Simulation } from '../../simulation/simulation.models';
import { SimulationService } from '../../simulation/simulation.service';
import {
  Application,
  BorrowerRequest,
  Financials,
  FinancialsRequest,
  PropertyRequest,
} from '../application.models';
import { ApplicationService } from '../application.service';
import { STATUS_CHIPS } from '../status-chip';
import { BorrowerFormControls, BorrowerStepComponent } from '../components/borrower-step.component';
import {
  FinancesFormControls,
  FinancesSectionComponent,
} from '../components/finances-section.component';
import { ProposalPromptComponent, ProposalRow } from '../components/proposal-prompt.component';
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
    RouterLink,
    Stepper,
    StepList,
    StepItem,
    StepPanels,
    StepPanel,
    Step,
    BorrowerStepComponent,
    PropertyStepComponent,
    ReviewStepComponent,
    ChecklistComponent,
    FinancesSectionComponent,
    ProposalPromptComponent,
  ],
  templateUrl: './application-wizard.component.html',
})
export class ApplicationWizardComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly applicationService = inject(ApplicationService);
  private readonly simulationService = inject(SimulationService);
  private readonly documentsService = inject(DocumentsService);

  private readonly applicationId = this.route.snapshot.paramMap.get('id') ?? '';

  /** UI-053, shared with the applications list so the two cannot disagree. */
  protected readonly statusChips = STATUS_CHIPS;

  protected readonly activeStep = signal(1);
  protected readonly application = signal<Application | null>(null);
  protected readonly simulation = signal<Simulation | null>(null);
  protected readonly submitting = signal(false);
  protected readonly checklist = signal<Checklist | null>(null);
  protected readonly rowStatus = signal<Record<string, RowStatus>>({});
  protected readonly financials = signal<Financials | null>(null);
  /** Every proposal the uploaded documents made, gathered from the checklist (T58). */
  protected readonly proposals = computed(() =>
    (this.checklist()?.items ?? [])
      .flatMap((item) => item.documents)
      .map((document) => document.proposal)
      .filter((proposal): proposal is DocumentProposal => proposal !== null),
  );
  protected readonly savingFinancials = signal(false);
  /**
   * `VAL-027` step 11, `SCP-022`, `DOC-005`. The checklist is *derived* from
   * the borrower's answers, so picking the wrong employment type once left
   * them with the wrong list for good: the wizard renders for `DRAFT` only and
   * there was no other way back to those fields. The API always allowed the
   * PATCH — it is refused only from `UNDER_REVIEW` on — so only the way in was
   * missing.
   */
  protected readonly editingAnswers = signal(false);
  protected readonly savingAnswers = signal(false);
  /**
   * `VAL-027` step 15. A URL naming an application that does not exist — or
   * somebody else's, which the API deliberately makes indistinguishable
   * (`AUTH-035`) — returned 404 and the page then rendered nothing at all:
   * a header over an empty white screen, with no way to tell a missing
   * application from a page that had not finished loading.
   */
  protected readonly notFound = signal(false);

  // The manual-entry base case (DOM-030). Extraction, once it exists,
  // pre-fills exactly these controls and changes nothing else here.
  protected readonly financesForm = new FormGroup<FinancesFormControls>({
    net_monthly_income: new FormControl<number | null>(null),
    existing_credit_monthly: new FormControl<number | null>(null),
    dependants: new FormControl(0, { nonNullable: true }),
  });

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
      .subscribe({
        next: (simulation) => this.simulation.set(simulation),
        error: () => this.notFound.set(true),
      });
  }

  protected onFileSelected({ docType, file }: FileSelection): void {
    this.setRowStatus(docType, { status: 'uploading', errorMessage: null });
    this.documentsService.upload(this.applicationId, docType, file).subscribe({
      next: (document) => {
        this.setRowStatus(docType, { status: 'idle', errorMessage: null });
        this.application.update((application) =>
          application ? { ...application, status: document.application_status } : application,
        );
        this.refreshChecklist();
      },
      error: (error: unknown) => {
        this.setRowStatus(docType, { status: 'error', errorMessage: this.messageFor(error) });
      },
    });
  }

  protected onDocumentRemoved({ documentId }: DocumentRemoval): void {
    this.documentsService.delete(this.applicationId, documentId).subscribe((result) => {
      this.application.update((application) =>
        application ? { ...application, status: result.application_status } : application,
      );
      this.refreshChecklist();
    });
  }

  protected onSaveFinancials(request: FinancialsRequest): void {
    if (this.savingFinancials()) {
      return;
    }
    this.savingFinancials.set(true);
    this.applicationService.putFinancials(this.applicationId, request).subscribe({
      next: (financials) => {
        this.financials.set(financials);
        this.savingFinancials.set(false);
      },
      error: () => {
        this.savingFinancials.set(false);
      },
    });
  }

  protected onAcceptProposal(row: ProposalRow): void {
    // Fills the form and stops. The borrower still presses "Save and assess",
    // so accepting a reading is never the same action as confirming it
    // (DOM-030) — nothing is stored until they say so.
    this.financesForm.patchValue({ [row.field]: Number(row.proposed) });
  }

  private refreshFinancials(): void {
    this.applicationService.financials(this.applicationId).subscribe((financials) => {
      this.financials.set(financials);
      this.financesForm.patchValue({
        net_monthly_income: financials.net_monthly_income
          ? Number(financials.net_monthly_income.amount)
          : null,
        existing_credit_monthly: financials.existing_credit_monthly
          ? Number(financials.existing_credit_monthly.amount)
          : null,
        dependants: financials.dependants,
      });
    });
  }

  private refreshChecklist(): void {
    this.documentsService
      .checklist(this.applicationId)
      .subscribe((checklist) => this.checklist.set(checklist));
  }

  private setRowStatus(docType: string, status: RowStatus): void {
    this.rowStatus.update((current) => ({ ...current, [docType]: status }));
  }

  private messageFor(error: unknown): string {
    if (error instanceof HttpErrorResponse) {
      const body = error.error as ApiError | undefined;
      if (body?.message) {
        return body.message;
      }
    }
    return 'Something went wrong. Please try again.';
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
        this.refreshChecklist();
      },
      error: () => {
        this.submitting.set(false);
      },
    });
  }

  protected toggleAnswers(): void {
    this.editingAnswers.update((open) => !open);
  }

  protected saveAnswers(): void {
    if (this.borrowerForm.invalid || this.propertyForm.invalid) {
      this.borrowerForm.markAllAsTouched();
      this.propertyForm.markAllAsTouched();
      return;
    }
    if (this.savingAnswers()) {
      return;
    }
    this.savingAnswers.set(true);
    this.applicationService
      .patch(this.applicationId, {
        borrowers: [this.borrowerPayload()],
        property: this.propertyPayload(),
      })
      .subscribe({
        next: (application) => {
          this.application.set(application);
          this.savingAnswers.set(false);
          this.editingAnswers.set(false);
          // The whole point of the edit: the derived list changes with the
          // answer that derives it.
          this.refreshChecklist();
        },
        error: () => this.savingAnswers.set(false),
      });
  }

  private borrowerPayload(): BorrowerRequest {
    const raw = this.borrowerForm.getRawValue();
    return {
      ...raw,
      monthly_net_income:
        raw.monthly_net_income === null ? null : raw.monthly_net_income.toFixed(2),
    };
  }

  private propertyPayload(): PropertyRequest {
    const raw = this.propertyForm.getRawValue();
    return { ...raw, purchase_price: raw.purchase_price.toFixed(2) };
  }

  private saveBorrower(): void {
    if (this.borrowerForm.invalid) {
      this.borrowerForm.markAllAsTouched();
      return;
    }
    this.applicationService
      .patch(this.applicationId, { borrowers: [this.borrowerPayload()] })
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
    this.applicationService
      .patch(this.applicationId, { property: this.propertyPayload() })
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
    if (application.status !== 'DRAFT') {
      this.refreshChecklist();
      this.refreshFinancials();
    }
  }
}
