import { test, expect, Page, Locator } from '@playwright/test';
import * as fs from 'fs';
import { PROJECT_PATH } from '../playwright.config';

/**
 * End-to-end checks of the S3 -> AI-built pipeline -> GCS -> schedule journey.
 * No fixed sleeps: every wait is on a visible UI state.
 * Selectors come from an inspection of the live app (data-testid, ARIA roles, React Flow ids).
 * Side effect: records the app's JSON API calls to api-tests/captured-endpoints.json
 * so the API tests call the real backend endpoints the UI uses.
 */

const captured: Record<string, { method: string; url: string; status: number }> = {};

test.beforeEach(async ({ page }) => {
  // Rhombus shows an "Ad Blocker Detected" modal in automated browsers; it blocks all clicks.
  // Dismiss it automatically whenever it appears.
  await page.addLocatorHandler(page.getByRole('dialog', { name: 'Ad Blocker Detected' }), async (dlg) => {
    await dlg.getByRole('button', { name: 'Continue Anyway' }).click();
  });

  page.on('response', async (res) => {
    const req = res.request();
    if (!['xhr', 'fetch'].includes(req.resourceType())) return;
    if (!(res.headers()['content-type'] ?? '').includes('json')) return;
    const u = new URL(res.url());
    captured[`${req.method()} ${u.origin}${u.pathname}`] = { method: req.method(), url: `${u.origin}${u.pathname}`, status: res.status() };
  });

  // The test browser starts from the saved login state, which also holds an old canvas position
  // (pan/zoom) that leaves the nodes off-screen. Clear it so the canvas opens at its default view,
  // the same as in a normal browser.
  await page.addInitScript(() => {
    try {
      for (const k of Object.keys(localStorage)) {
        if (/viewport|reactflow|react-flow|canvas|zoom|pan|flow/i.test(k)) localStorage.removeItem(k);
      }
    } catch { /* storage unavailable */ }
  });
  await page.goto(PROJECT_PATH);
  await expect(page.getByRole('tab', { name: 'Canvas' })).toBeVisible();
  await expect(page.getByTestId('run-pipeline')).toBeVisible();
});

test.afterAll(() => {
  fs.writeFileSync('api-tests/captured-endpoints.json', JSON.stringify(Object.values(captured), null, 2));
});

async function drag(page: Page, dx: number) {
  await page.mouse.move(dx < 0 ? 950 : 450, 750);
  await page.mouse.down();
  await page.mouse.move(dx < 0 ? 450 : 950, 750, { steps: 10 });
  await page.mouse.up();
}

/**
 * Rhombus only renders canvas nodes that are on screen, and it saves the canvas position.
 * Search for the node by panning left, then right, and return the net number of pans
 * so the caller can put the canvas back exactly where it was.
 */
async function bringIntoView(page: Page, node: Locator): Promise<number> {
  let net = 0; // negative = panned left
  const seen = async () => node.isVisible();
  const MAX = 15;
  for (let i = 0; i < MAX && !(await seen()); i++) { await drag(page, -1); net--; }
  while (net < 0 && !(await seen())) { await drag(page, +1); net++; } // back to start
  for (let i = 0; i < MAX && !(await seen()); i++) { await drag(page, +1); net++; }
  await expect(node, 'node not found after panning the canvas both ways').toBeVisible({ timeout: 5_000 });
  return net;
}

async function restoreView(page: Page, net: number) {
  await page.keyboard.press('Escape');
  for (let i = 0; i < Math.abs(net); i++) await drag(page, net < 0 ? +1 : -1);
}

test('1. S3 source is connected', async ({ page }) => {
  // The "+" next to "Facet" in the AI Builder chat box opens the data-source menu.
  await page.getByRole('button', { name: 'Facet' }).locator('xpath=preceding::button[1]').click();
  await page.getByText(/Third[- ]party sources/i).click();
  await expect(page.getByText('orders-source')).toBeVisible();
  await expect(page.getByText('Connected').first()).toBeVisible();
  await expect(page.getByText('s3://speranza-rhombus-source', { exact: true })).toBeVisible();
  await expect(page.getByText(/ap-southeast-2/)).toBeVisible();
});

test('2. AI-built pipeline is on the canvas', async ({ page }) => {
  const nodes = page.locator('[data-testid^="rf__node-"]');
  // The AI Builder's chain starts with a text-cleanup step followed by AI ("Custom") cleaning steps.
  await expect(nodes.filter({ hasText: 'Text Cleanup' }).first()).toBeVisible();
  await expect.poll(() => nodes.filter({ hasText: 'Custom' }).count(), { message: 'AI-built cleaning steps on the canvas' })
    .toBeGreaterThanOrEqual(4);
  // The steps are linked into a chain (React Flow draws one edge per link).
  await expect.poll(() => page.locator('.react-flow__edge').count(), { message: 'connected steps' })
    .toBeGreaterThanOrEqual(4);
  // ...and the chain ends in a Data Output node (further right on the canvas).
  const output = nodes.filter({ hasText: 'Data Output' });
  const net = await bringIntoView(page, output);
  await expect(output).toHaveCount(1);
  await restoreView(page, net);
});

test('3. Output node exports to the GCS bucket', async ({ page }) => {
  const output = page.locator('[data-testid^="rf__node-"]').filter({ hasText: 'Data Output' });
  const net = await bringIntoView(page, output);
  await output.click();
  await expect(page.getByText('Select Destination')).toBeVisible();
  const panel = page.getByRole('complementary');
  const gcs = panel.getByRole('button', { name: 'Google Cloud Storage speranza-rhombus-output' });
  const local = panel.getByRole('button', { name: /^Download Locally/ });
  await expect(gcs).toBeVisible();
  // Destinations are buttons with no ARIA "selected" state (see usability notes), so the
  // selected one is detected by its highlight: GCS must be styled differently from Download Locally.
  const bg = (l: Locator) => l.evaluate((el) => getComputedStyle(el).backgroundColor);
  expect(await bg(gcs), 'GCS destination should be highlighted as selected').not.toBe(await bg(local));
  // Export settings that the data-validation step relies on.
  await expect(panel.getByRole('combobox')).toHaveText(/CSV/);
  await expect(panel.getByRole('textbox', { name: 'RhombusAI_output' })).toHaveValue('orders_cleaned');
  await restoreView(page, net);
});

test('4. Pipeline has a schedule', async ({ page }) => {
  await page.getByRole('tab', { name: 'Schedule' }).click();
  await expect(page.getByText(/Manage schedules within this project/i)).toBeVisible();
  // The schedule card for this pipeline is listed, active, daily, and switched on.
  const card = page.getByText(/Schedule for S3-to-GCS-cleaning-pipeline/).first();
  await expect(card).toBeVisible();
  await expect(page.getByText(/daily/i).first()).toBeVisible();
  await expect(page.getByText('Active', { exact: true }).first()).toBeVisible();
  await expect(page.getByRole('switch', { name: 'Deactivate schedule' })).toBeChecked();
  await expect(page.getByText(/no schedules found/i)).toHaveCount(0);
});

test('5. Manual run completes and logs success', async ({ page }) => {
  await page.getByRole('button', { name: 'Logs' }).click();
  const started = page.getByText('Pipeline execution started.');
  const done = page.getByText(/Pipeline (execution )?completed successfully/);
  const failed = page.getByText(/Pipeline failed at/);
  const before = { started: await started.count(), done: await done.count(), failed: await failed.count() };

  // The Run button must actually start a backend job (the same call the UI makes).
  const [proc] = await Promise.all([
    page.waitForResponse((r) => /\/pipeline\/process/.test(r.url()) && r.request().method() === 'POST', { timeout: 60_000 }),
    page.getByTestId('run-pipeline').click(),
  ]);
  expect(proc.status(), 'pipeline/process should accept the run').toBe(200);
  // Wait for this run to finish one way or the other.
  await expect(async () => {
    expect((await done.count()) + (await failed.count()), 'no completion line in Logs yet').toBeGreaterThan(before.done + before.failed);
  }).toPass({ timeout: 150_000, intervals: [2_000, 5_000] });
  // Real outcome: this run must not have logged a failure (Rhombus can log both - see findings).
  expect(await failed.count(), 'this run logged "Pipeline failed at ..."').toBe(before.failed);
});
