import { TestBed } from '@angular/core/testing';

import { DocumentProposal } from '../../documents/documents.models';
import { ProposalPromptComponent } from './proposal-prompt.component';

function payslipProposal(income: string | null): DocumentProposal {
  return {
    net_monthly_income: income,
    existing_credit_monthly: null,
    source: 'your payslip',
  };
}

async function render(proposals: DocumentProposal[], current: string | null) {
  await TestBed.configureTestingModule({ imports: [ProposalPromptComponent] }).compileComponents();
  const fixture = TestBed.createComponent(ProposalPromptComponent);
  fixture.componentRef.setInput('proposals', proposals);
  fixture.componentRef.setInput('currentIncome', current);
  fixture.detectChanges();
  return fixture;
}

describe('ProposalPromptComponent', () => {
  it('shows both figures when a document disagrees with what was entered', async () => {
    const fixture = await render([payslipProposal('3200.00')], '3000.00');

    const text = fixture.nativeElement.textContent;
    expect(text).toContain('3.200,00');
    expect(text).toContain('3.000,00');
    expect(text).toContain('your payslip');
  });

  it('shows a confirmed figure as reconciled, with nothing left to accept', async () => {
    // Agreement is the thing worth demonstrating. Hiding a row the moment it
    // matched removed the evidence exactly when it became meaningful: the
    // borrower had no way to see that the assessment was running on the figure
    // their payslip actually stated.
    const fixture = await render([payslipProposal('3200.00')], '3200.00');

    const rendered = fixture.nativeElement.textContent;
    expect(rendered).toContain('Checked against your documents');
    expect(rendered).toContain('confirmed unchanged');
    expect(fixture.nativeElement.querySelector('button')).toBeNull();
  });

  it('says nothing when a document read no figure at all', async () => {
    const fixture = await render([payslipProposal(null)], '3000.00');

    expect(fixture.nativeElement.textContent.trim()).toBe('');
  });

  it('emits the accepted row rather than applying it itself (DOM-030)', async () => {
    const fixture = await render([payslipProposal('3200.00')], '3000.00');
    const accepted: string[] = [];
    fixture.componentInstance.accept.subscribe((row) => accepted.push(row.proposed));

    fixture.nativeElement.querySelector('button').click();

    expect(accepted).toEqual(['3200.00']);
  });
});
