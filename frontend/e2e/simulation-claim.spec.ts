import { expect, test } from '@playwright/test';

function uniqueEmail(): string {
  return `e2e-claim-${Date.now()}-${Math.floor(Math.random() * 10_000)}@example.com`;
}

// DOM-026, corrected at T62. Found by hand while verifying T55: the simulation
// id lived only in a signal, so a hard reload between simulating and signing
// up silently dropped it. Signup still succeeded (UX-028), but the draft was
// created unseeded — and with T53/T54 in place that also means the
// affordability assessment has no instalment to measure against (API-075).
test('a reload between simulating and signing up still claims the simulation', async ({ page }) => {
  await page.goto('/calculator');
  await expect(page.getByText('1.414,52')).toBeVisible();

  // A full page load, not a router navigation: this is the borrower typing the
  // address, or refreshing, and it is what used to lose the simulation.
  await page.goto('/signup');
  await page.locator('#email').fill(uniqueEmail());
  await page.locator('#password').fill('hunter2hunter2');

  const created = page.waitForResponse(
    (response) =>
      response.url().includes('/api/applications') && response.request().method() === 'POST',
  );
  await page.getByRole('button', { name: 'Sign up' }).click();

  const body = (await (await created).json()) as {
    simulation_id: string | null;
    property: { purchase_price: string } | null;
  };
  expect(body.simulation_id).not.toBeNull();
  expect(body.property?.purchase_price).toBe('300000.00');
});
