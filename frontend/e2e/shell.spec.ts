import { expect, test } from '@playwright/test';

/**
 * The one scenario T26 itself needs proven: Playwright is wired end to end
 * and the shell renders. The five scenarios the plan names — UX-055/056/057
 * (T27), UX-059 (T29), UX-061/UI-067 (T30) — land with the pages they test.
 */
test('the header renders the product name', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('header')).toContainText('Borrower Portal');
});

// T46: root moved from the simulator to the marketing home page.
test('the home page renders its hero and both CTAs navigate correctly', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

  await page.getByRole('link', { name: 'Calculate your mortgage' }).click();
  await expect(page).toHaveURL(/\/calculator$/);

  await page.goBack();
  await page.getByRole('link', { name: 'Get started' }).first().click();
  await expect(page).toHaveURL(/\/signup$/);
});
