import { test, expect } from '@playwright/test';
import { STORAGE } from '../playwright.config';

/**
 * Run once:  npm run auth
 * A browser opens on Rhombus. Log in normally (email or Google).
 * When your dashboard/project loads, the session is saved and the browser closes.
 */
test('log in manually and save session', async ({ page }) => {
  test.setTimeout(5 * 60_000);
  await page.goto('/');
  // Wait (up to 5 min) until the logged-in app is visible.
  await expect(page.getByText(/Dashboard|All Projects|New Project/).first()).toBeVisible({ timeout: 5 * 60_000 });
  await page.context().storageState({ path: STORAGE });
});
