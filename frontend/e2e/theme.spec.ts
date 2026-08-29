import { expect, test } from '@playwright/test';

// UX-064: the toggle flips the whole app and the choice survives a reload —
// proven against a real page rather than just the service in isolation
// (theme.service.spec.ts covers the persistence logic itself).
test('the theme toggle flips the app and survives a reload', async ({ page }) => {
  await page.goto('/');
  const html = page.locator('html');
  await expect(html).not.toHaveClass(/dark/);

  await page.locator('header button[aria-label="Switch to dark theme"]').click();
  await expect(html).toHaveClass(/dark/);

  await page.reload();
  await expect(html).toHaveClass(/dark/);

  await page.locator('header button[aria-label="Switch to light theme"]').click();
  await expect(html).not.toHaveClass(/dark/);
});
