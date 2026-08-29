import { expect, test } from '@playwright/test';

function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 10_000)}@example.com`;
}

test('signup carries the simulator session forward into a prefilled application', async ({
  page,
}) => {
  // Visits the simulator first so SimulationService.lastId() is actually set
  // before signup — root is the marketing home page (T46) and makes no
  // simulate() call of its own. Navigates to /signup directly afterwards
  // rather than through the header's links — that link is a trivial
  // routerLink and is not what this test is about.
  await page.goto('/calculator');
  await expect(page.getByText('1.414,52')).toBeVisible();

  await page.goto('/signup');
  await page.locator('#email').fill(uniqueEmail());
  await page.locator('#password').fill('hunter2hunter2');

  // UX-027: signup only claims the simulation; the draft it seeds is created
  // by the very next call. There is no wizard page to land on yet (T29), so
  // this asserts the network contract the flow actually depends on rather
  // than a route that does not exist in this batch.
  const createApplication = page.waitForResponse(
    (response) =>
      response.url().includes('/api/applications') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Sign up' }).click();

  const response = await createApplication;
  expect(response.status()).toBe(201);
  const body = (await response.json()) as { id: string };
  expect(body.id).toBeTruthy();
});
