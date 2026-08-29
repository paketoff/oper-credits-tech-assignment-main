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

    expect(fixture.nativeElement.textContent).toContain('1 of 2 required documents uploaded.');
  });
});
