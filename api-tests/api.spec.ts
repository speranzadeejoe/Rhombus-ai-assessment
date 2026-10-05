import { test, expect, request, APIRequestContext } from '@playwright/test';
import * as fs from 'fs';

/**
 * Backend API tests against the real endpoints the Rhombus UI calls
 * (recorded by the UI tests into api-tests/captured-endpoints.json).
 *
 * Auth model (observed): the web app (rhombusai.com) holds a login-cookie session;
 * the API (api.rhombusai.com) does NOT accept that cookie (401) and needs a bearer
 * token, which the app gets from rhombusai.com/api/auth/session.
 */

const PROJECT_ID = '4190';
const API = 'https://api.rhombusai.com/api';
const SCHEDULES = `${API}/dataset/analyzer/v2/projects/${PROJECT_ID}/pipeline/schedules`;
const SESSION = 'https://rhombusai.com/api/auth/session';

/** Find the first JWT-like / token-named string anywhere in a JSON object. */
function findToken(o: unknown): string | undefined {
  if (!o || typeof o !== 'object') return;
  for (const [k, v] of Object.entries(o as Record<string, unknown>)) {
    if (typeof v === 'string' && /token/i.test(k) && !/refresh|csrf/i.test(k) && v.length > 20) return v;
    const nested = findToken(v);
    if (nested) return nested;
  }
}

async function getToken(authed: APIRequestContext): Promise<string | undefined> {
  if (process.env.RHOMBUS_TOKEN) return process.env.RHOMBUS_TOKEN;
  const res = await authed.get(SESSION);
  if (res.ok()) {
    const t = findToken(await res.json().catch(() => ({})));
    if (t) return t;
  }
  // Fallback: token kept in localStorage of the saved login state.
  const state = JSON.parse(fs.readFileSync('.auth/state.json', 'utf8'));
  for (const origin of state.origins ?? []) {
    for (const { name, value } of origin.localStorage ?? []) {
      if (/token/i.test(name) && value.length > 20) {
        try { return findToken(JSON.parse(value)) ?? value; } catch { return value; }
      }
    }
  }
}

test.describe('Rhombus backend API', () => {
  test('authenticated GET of pipeline schedules returns 200 with the daily schedule', async ({ request: authed }) => {
    const token = await getToken(authed);
    expect(token, 'no API token found in session - rerun `npm run auth`').toBeTruthy();
    const api = await request.newContext({ extraHTTPHeaders: { Authorization: `Bearer ${token}` } });
    const res = await api.get(SCHEDULES);
    expect(res.status()).toBe(200);
    expect(res.headers()['content-type']).toContain('json');
    const body = JSON.stringify(await res.json());
    expect(body.length).toBeGreaterThan(2);       // not {} / []
    expect(body).toMatch(/daily/i);                // the schedule set up in the UI
    await api.dispose();
  });

  test('NEGATIVE: unauthenticated request is rejected', async () => {
    const anon = await request.newContext(); // no cookies, no token
    const res = await anon.get(SCHEDULES);
    expect([401, 403]).toContain(res.status());
    expect(await res.text()).not.toMatch(/daily|speranza-rhombus/i); // no private data leaked
    await anon.dispose();
  });

  test('NEGATIVE: forged bearer token is rejected', async () => {
    const forged = await request.newContext({ extraHTTPHeaders: { Authorization: 'Bearer invalid.token.value' } });
    const res = await forged.get(SCHEDULES);
    expect([401, 403]).toContain(res.status());
    await forged.dispose();
  });
});
