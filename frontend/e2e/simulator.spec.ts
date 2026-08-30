import { expect, test } from '@playwright/test';

/**
 * UX-055 - UX-057, proven against the real backend rather than a mocked
 * service — these are claims about a rendered page, not about the code that
 * renders it.
 */
test('the result panel holds a computed figure on first paint, with no interaction', async ({
  page,
}) => {
  await page.goto('/calculator');

  await expect(page.getByText('1.414,52')).toBeVisible();
});

test('changing an input never empties the previous result', async ({ page }) => {
  await page.goto('/calculator');
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
  await page.goto('/calculator');

  const contribution = page.locator('#own_contribution');
  await contribution.click();
  await contribution.fill('0');
  await contribution.blur();

  const chip = page.getByRole('status');
  await expect(chip).toBeVisible({ timeout: 5000 });
  await expect(chip).toContainText('90%');
  await expect(chip).not.toHaveClass(/danger/);
});

// UX-063: a real bug, found by the user by hand — typing into a plain
// number field (not via a spinner's arrows) can pass through an invalid
// intermediate value (the field briefly empty), which used to send a
// request the backend rejected and permanently kill all future recompute.
test('clearing a field mid-edit and retyping does not freeze future recompute', async ({
  page,
}) => {
  await page.goto('/calculator');
  await expect(page.getByText('1.414,52')).toBeVisible();

  const term = page.locator('#term_months');
  await term.fill('');
  await page.waitForTimeout(400);
  await term.fill('180');

  await expect(page.getByText('1.414,52')).not.toBeVisible({ timeout: 5000 });
});

// The borrower's own figures survive leaving the page and coming back. The
// form was rebuilt from the prefilled primary case on every visit, so typing
// 200 000 and navigating away silently restored 300 000 — and the first paint
// then recomputed from those defaults, replacing the simulation they had just
// made with one they never asked for.
test('the figures typed into the calculator survive leaving and returning', async ({ page }) => {
  await page.goto('/calculator');
  await expect(page.getByText('1.414,52')).toBeVisible();

  await page.locator('#property_value').click();
  await page.keyboard.press('ControlOrMeta+a');
  await page.keyboard.type('200000');
  await page.keyboard.press('Tab');
  await expect(page.getByText('1.414,52')).toBeHidden();

  await page.goto('/');
  await page.goto('/calculator');

  await expect(page.locator('#property_value')).toHaveValue(/200\.000/);
});
