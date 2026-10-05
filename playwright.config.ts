import { defineConfig, devices } from '@playwright/test';

export const STORAGE = '.auth/state.json';
export const BASE_URL = process.env.RHOMBUS_URL ?? 'https://rhombusai.com';
// Browser for the UI tests: installed Microsoft Edge by default. Set PW_CHANNEL=chromium to use Playwright's bundled browser.
export const CHANNEL = process.env.PW_CHANNEL ?? 'msedge';
export const PROJECT_PATH = process.env.RHOMBUS_PROJECT ?? '/workflow/4190';

export default defineConfig({
  timeout: 240_000, // test 5 runs the real pipeline
  expect: { timeout: 30_000 },
  retries: 0,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    // One-time manual login (email or Google). Saves the session to .auth/state.json.
    { name: 'auth', testDir: './ui-tests', testMatch: /auth\.setup\.ts/, use: { ...devices['Desktop Chrome'] } },
    { name: 'ui', testDir: './ui-tests', testMatch: /.*\.spec\.ts/,
      use: { ...devices['Desktop Chrome'], channel: CHANNEL === 'chromium' ? undefined : CHANNEL, storageState: STORAGE, viewport: { width: 1600, height: 950 } } },
    { name: 'api', testDir: './api-tests', testMatch: /.*\.spec\.ts/, use: { storageState: STORAGE } },
  ],
});
