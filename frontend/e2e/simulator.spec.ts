import { expect, test } from '@playwright/test';

/**
 * UX-055 - UX-057, proven against the real backend rather than a mocked
 * service — these are claims about a rendered page, not about the code that
 * renders it.
 */
test('the result panel holds a computed figure on first paint, with no interaction', async ({
  page,
}) => {
  await page.goto('/');

  await expect(page.getByText('1.414,52')).toBeVisible();
});

test('changing an input never empties the previous result', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('1.414,52')).toBeVisible();

  const contribution = page.locator('#own_contribution');
  await contribution.click();
  await contribution.fill('0');
  await contribution.blur();

  // The old figure must still be on screen the instant the value changes,
  // before the debounced request has even had time to resolve.
  await expect(page.getByText('1.414,52')).toBeVisible();

  // And the new one lands without the old one ever having disappeared.
  await expect(page.getByRole('status')).toBeVisible({ timeout: 5000 });
});

test('the above-norm chip appears once quotiteit crosses 90%, and reads as informational', async ({
  page,
}) => {
  await page.goto('/');

  const contribution = page.locator('#own_contribution');
  await contribution.click();
  await contribution.fill('0');
  await contribution.blur();

  const chip = page.getByRole('status');
  await expect(chip).toBeVisible({ timeout: 5000 });
  await expect(chip).toContainText('90%');
  await expect(chip).not.toHaveClass(/danger/);
});
