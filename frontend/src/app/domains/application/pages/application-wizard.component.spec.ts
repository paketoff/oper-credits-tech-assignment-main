import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap } from '@angular/router';

import { Application } from '../application.models';
import { ApplicationWizardComponent } from './application-wizard.component';

function draftApplication(overrides: Partial<Application> = {}): Application {
  return {
    id: 'app-1',
    status: 'DRAFT',
    simulation_id: null,
    borrowers: [],
    property: null,
    submitted_at: null,
    created_at: 'x',
    updated_at: 'x',
    ...overrides,
  };
}

describe('ApplicationWizardComponent', () => {
  let httpMock: HttpTestingController;

  async function createFixture(application: Application = draftApplication()) {
    await TestBed.configureTestingModule({
      imports: [ApplicationWizardComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ id: 'app-1' }) } },
        },
      ],
    }).compileComponents();
    httpMock = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(ApplicationWizardComponent);
    fixture.detectChanges();
    httpMock.expectOne('/api/applications/app-1').flush(application);
    fixture.detectChanges();
    return fixture;
  }

  it('only validates the current step: an invalid step 1 does not advance', async () => {
    const fixture = await createFixture();

    // Never touched: full_name and date_of_birth are empty, which is invalid.
    fixture.componentInstance['next']();

    expect(fixture.componentInstance['activeStep']()).toBe(1);
    httpMock.verify();
  });

  it('advances past step 1 and saves the draft server-side (UX-033)', async () => {
    const fixture = await createFixture();
    fixture.componentInstance['borrowerForm'].setValue({
      full_name: 'Jan Test',
      date_of_birth: '1990-04-12',
      employment_type: 'EMPLOYEE',
      monthly_net_income: 3200,
      has_existing_credit: false,
    });

    fixture.componentInstance['next']();

    const request = httpMock.expectOne('/api/applications/app-1');
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body.borrowers[0].full_name).toBe('Jan Test');
    request.flush(
      draftApplication({
        borrowers: [
          {
            id: 'b1',
            full_name: 'Jan Test',
            date_of_birth: '1990-04-12',
            employment_type: 'EMPLOYEE',
            monthly_net_income: '3200.00',
            has_existing_credit: false,
          },
        ],
      }),
    );

    expect(fixture.componentInstance['activeStep']()).toBe(2);
    httpMock.verify();
  });

  it('back preserves what was already entered (UX-031)', async () => {
    const fixture = await createFixture();
    fixture.componentInstance['borrowerForm'].setValue({
      full_name: 'Jan Test',
      date_of_birth: '1990-04-12',
      employment_type: 'EMPLOYEE',
      monthly_net_income: null,
      has_existing_credit: false,
    });
    fixture.componentInstance['next']();
    httpMock.expectOne('/api/applications/app-1').flush(
      draftApplication({
        borrowers: [
          {
            id: 'b1',
            full_name: 'Jan Test',
            date_of_birth: '1990-04-12',
            employment_type: 'EMPLOYEE',
            monthly_net_income: null,
            has_existing_credit: false,
          },
        ],
      }),
    );
    expect(fixture.componentInstance['activeStep']()).toBe(2);

    fixture.componentInstance['back']();

    expect(fixture.componentInstance['activeStep']()).toBe(1);
    expect(fixture.componentInstance['borrowerForm'].controls.full_name.value).toBe('Jan Test');
    httpMock.verify();
  });

  it('a failed upload reverts its row (UX-041)', async () => {
    const fixture = await createSubmittedFixture();

    fixture.componentInstance['onFileSelected']({
      docType: 'PAYSLIPS',
      file: new File(['x'], 'payslip.pdf', { type: 'application/pdf' }),
    });
    expect(fixture.componentInstance['rowStatus']()['PAYSLIPS'].status).toBe('uploading');

    httpMock
      .expectOne('/api/applications/app-1/documents')
      .flush(
        { code: 'DOCUMENT_TOO_LARGE', message: 'Files must be under 10 MB.', field: null },
        { status: 413, statusText: 'Payload Too Large' },
      );

    const row = fixture.componentInstance['rowStatus']()['PAYSLIPS'];
    expect(row.status).toBe('error');
    expect(row.errorMessage).toBe('Files must be under 10 MB.');
    httpMock.verify();
  });

  async function createSubmittedFixture() {
    const fixture = await createFixture(draftApplication({ status: 'SUBMITTED' }));
    httpMock
      .expectOne('/api/applications/app-1/checklist')
      .flush({ required_count: 1, satisfied_count: 0, items: [] });
    // A submitted application also loads its confirmed financials (T54): the
    // finances section is part of this page, not a separate screen.
    httpMock.expectOne('/api/applications/app-1/financials').flush({
      net_monthly_income: null,
      existing_credit_monthly: null,
      dependants: 0,
      assessment: null,
      updated_at: null,
    });
    fixture.detectChanges();
    return fixture;
  }
});
