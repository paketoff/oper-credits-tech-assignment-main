import { expect, test } from '@playwright/test';

function uniqueEmail(): string {
  return `e2e-flow-${Date.now()}-${Math.floor(Math.random() * 10_000)}@example.com`;
}

// UX-061: the whole flow — simulate, sign up, wizard, upload — completes on
// a 375px viewport (the `chromium-375` project). UI-067's keyboard check
// rides along: the sign-up submit below is triggered by focus + Enter, not
// a click.
test('simulate, sign up, complete the wizard and upload a document at 375px', async ({
  page,
}) => {
  await page.goto('/calculator');
  await expect(page.getByText('1.414,52')).toBeVisible();

  await page.goto('/signup');
  await page.locator('#email').fill(uniqueEmail());
  await page.locator('#password').fill('hunter2hunter2');
  const createApplication = page.waitForResponse(
    (response) =>
      response.url().includes('/api/applications') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Sign up' }).focus();
  await page.keyboard.press('Enter');
  const response = await createApplication;
  const { id } = (await response.json()) as { id: string };
  await page.goto(`/applications/${id}`);

  await page.locator('#full_name').fill('Jan Test');
  await page.locator('#date_of_birth').fill('1990-04-12');
  await page.getByRole('button', { name: 'Next' }).click();

  await expect(page.locator('#wizard_region')).toBeVisible();
  await page.getByRole('button', { name: 'Next' }).click();

  await page.getByRole('button', { name: 'Next' }).click();

  const submitted = page.waitForResponse((response) =>
    response.url().includes(`/api/applications/${id}/submit`),
  );
  await page.getByRole('button', { name: 'Submit application' }).click();
  await submitted;

  await expect(page.getByText('Application submitted')).toBeVisible();
  await expect(page.getByText(/required documents uploaded/)).toBeVisible();

  const uploaded = page.waitForResponse(
    (response) =>
      response.url().includes(`/api/applications/${id}/documents`) &&
      response.request().method() === 'POST',
  );
  await page.locator('input[type="file"]').first().setInputFiles({
    name: 'id.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4 test document'),
  });
  const uploadResponse = await uploaded;
  expect(uploadResponse.status()).toBe(201);
  await expect(page.getByText('Uploaded').first()).toBeVisible();
});
