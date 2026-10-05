# UI & API tests (Playwright)

Setup (once):
```bash
npm install
npx playwright install chromium
# Google blocks sign-in inside automated browsers, so log in in a normal Chrome window:
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir=%TEMP%\rhombus-profile https://rhombusai.com
# ...log in to Rhombus in that window, open your project, then in the tests folder:
npm run auth        # connects to that Chrome and saves the session to .auth/state.json
```

Run:
```bash
npm run test:ui     # S3 connected, AI pipeline on canvas, GCS destination, schedule, run succeeds
npm run test:api    # backend calls: 200 authed, 401/403 unauthenticated, 401/403 forged token
npm run report      # HTML report with traces/screenshots of failures
```

Optional env vars: `RHOMBUS_PROJECT=/workflow/<id>`, `RHOMBUS_API_ENDPOINT=<url>`.

No fixed sleeps: all waits are on visible UI state or network responses.
The session file `.auth/state.json` is git-ignored (contains your login cookies).
