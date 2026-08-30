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

  it('says nothing when the document agrees with what is already confirmed', async () => {
    // Proposing a figure the borrower already has is noise, not help.
    const fixture = await render([payslipProposal('3200.00')], '3200.00');

    expect(fixture.nativeElement.textContent.trim()).toBe('');
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
