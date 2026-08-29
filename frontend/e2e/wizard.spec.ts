import { expect, test } from '@playwright/test';

function uniqueEmail(): string {
  return `e2e-wizard-${Date.now()}-${Math.floor(Math.random() * 10_000)}@example.com`;
}

async function signUpAndReachWizard(page: import('@playwright/test').Page): Promise<string> {
  await page.goto('/signup');
  await page.locator('#email').fill(uniqueEmail());
  await page.locator('#password').fill('hunter2hunter2');
  const createApplication = page.waitForResponse(
    (response) =>
      response.url().includes('/api/applications') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Sign up' }).click();
  const response = await createApplication;
  const body = (await response.json()) as { id: string };
  await page.goto(`/applications/${body.id}`);
  return body.id;
}

test('a mid-wizard reload keeps what was entered after step 1 (UX-059)', async ({ page }) => {
  const id = await signUpAndReachWizard(page);

  await page.locator('#full_name').fill('Jan Test');
  await page.locator('#date_of_birth').fill('1990-04-12');
  const savedDraft = page.waitForResponse(
    (response) =>
      response.url().includes(`/api/applications/${id}`) && response.request().method() === 'PATCH',
  );
  await page.getByRole('button', { name: 'Next' }).click();
  await savedDraft;

  // UX-033: the draft is saved server-side, not just held in the browser.
  // Reloading lands back on step 1 — this build never promised the step
  // *position* survives, only the input — and the borrower's name is still
  // there because the server, not the tab, is the source of truth for it.
  await page.goto(`/applications/${id}`);

  await expect(page.locator('#full_name')).toHaveValue('Jan Test');
  await expect(page.locator('#date_of_birth')).toHaveValue('1990-04-12');
});
