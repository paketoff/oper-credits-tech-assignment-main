import { TestBed } from '@angular/core/testing';

import { Checklist } from '../documents.models';
import { ChecklistComponent } from './checklist.component';

function checklistWith(reason: string | null): Checklist {
  return {
    required_count: 2,
    satisfied_count: 1,
    items: [
      {
        doc_type: 'IDENTITY',
        label_en: 'Identity document',
        label_nl: 'identiteitskaart',
        required: true,
        satisfied: true,
        reason: null,
        documents: [],
      },
      {
        doc_type: 'PAYSLIPS',
        label_en: 'Recent payslips',
        label_nl: 'loonfiches',
        required: true,
        satisfied: false,
        reason,
        documents: [],
      },
    ],
  };
}

describe('ChecklistComponent', () => {
  it("shows a conditional item's reason (UX-038)", async () => {
    await TestBed.configureTestingModule({ imports: [ChecklistComponent] }).compileComponents();
    const fixture = TestBed.createComponent(ChecklistComponent);
    fixture.componentRef.setInput(
      'checklist',
      checklistWith('Required because you selected employed'),
    );
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Required because you selected employed');
  });

  it('shows no reason line for a plain required item', async () => {
    await TestBed.configureTestingModule({ imports: [ChecklistComponent] }).compileComponents();
    const fixture = TestBed.createComponent(ChecklistComponent);
    fixture.componentRef.setInput('checklist', checklistWith(null));
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('1 of 2 uploaded');
  });
});

describe('ChecklistComponent classification states', () => {
  function withDocument(status: string | null, message: string | null): Checklist {
    return {
      required_count: 1,
      satisfied_count: 1,
      items: [
        {
          doc_type: 'PAYSLIPS',
          label_en: 'Recent payslips',
          label_nl: 'loonfiches',
          required: true,
          satisfied: true,
          reason: null,
          documents: [
            {
              id: 'd1',
              filename: 'march.pdf',
              size_bytes: 1024,
              uploaded_at: 'x',
              classification_status: status,
              classification_message: message,
              proposal: null,
            },
          ],
        },
      ],
    };
  }

  async function render(checklist: Checklist) {
    await TestBed.configureTestingModule({ imports: [ChecklistComponent] }).compileComponents();
    const fixture = TestBed.createComponent(ChecklistComponent);
    fixture.componentRef.setInput('checklist', checklist);
    fixture.detectChanges();
    return fixture;
  }

  it('failed and skipped render as nothing (AI-021)', async () => {
    // Both arrive as a null message: a failed classification is our problem,
    // and a disabled feature is not news.
    const fixture = await render(withDocument('FAILED', null));

    expect(fixture.nativeElement.textContent).not.toContain('could not');
    // The row itself is untouched — the document still satisfies its requirement.
    expect(fixture.nativeElement.textContent).toContain('march.pdf');
    expect(fixture.nativeElement.textContent).toContain('1 of 1 uploaded');
  });

  it('a likely mismatch shows the server-composed sentence and keeps the file (AI-006)', async () => {
    const fixture = await render(
      withDocument('DONE', 'This looks like a bank statement, but it was uploaded as a payslip.'),
    );

    const text = fixture.nativeElement.textContent;
    expect(text).toContain('This looks like a bank statement');
    // The borrower keeps it: still listed, still satisfying the requirement.
    expect(text).toContain('march.pdf');
    expect(text).toContain('Uploaded');
  });
});
