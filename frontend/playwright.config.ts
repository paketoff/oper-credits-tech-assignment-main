import { defineConfig, devices } from '@playwright/test';

/**
 * Five browser scenarios that turn UI-066, UI-067, UX-055, UX-056, UX-057,
 * UX-059 and UX-061 into a gate rather than a memory (UI-068, UX-062).
 * Chromium only: this is a gate, not a cross-browser suite.
 *
 * Assumes the built app is already being served — `webServer` is left unset
 * deliberately, because the suite needs the real backend behind `/api` too
 * (the proxy in `proxy.conf.json`), not a static file server. `make test`
 * starts `ng serve` and `uvicorn` itself before invoking Playwright.
 */
export default defineConfig({
  testDir: './e2e',
  // Serial, not parallel. Every scenario shares one backend process and one
  // SQLite file; several browser contexts hitting it at once produced a real
  // timing flake under load, not a bug in the app itself. This suite is five
  // or six tests — correctness matters far more here than wall-clock speed.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env['CI'],
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:4200',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'chromium-375',
      testMatch: /375\.spec\.ts$/,
      use: { ...devices['Desktop Chrome'], viewport: { width: 375, height: 667 } },
    },
  ],
});
