## Guide addendum: browser tests of the frontend (fe-dev)

**You also test the deployed frontend in a real browser** with Playwright (`@playwright/test` is already in `agenthub-frontend/package.json`). The target is `https://www.4genthub.com`. This is the same seat that owns the existing surfaces, so a defect you find in a page you own you fix; a defect in a surface web-dev owns goes to the lead.

### The test account
- The login lives in `/home/daihu/__projects__/4genthub/e2e-test-account`: two lines, `USERNAME=` and `PASSWORD=`. The file is gitignored (`/e2e-test-account`) and mode 600.
- Read it **inside the test process** (Playwright config or a fixture parses the file and fills the login form). Never `cat`, `grep`, `echo` or `print` it, never paste a value into a task, message, log, screenshot, trace, test title or commit, and never copy the file.
- Keep Playwright traces, videos and screenshots out of git (`test-results/`, `playwright-report/`) and look at a screenshot before you attach it: a filled password field is a leak.
- The account is a shared test user on production. Read and navigate; create only data you delete again in the same test; never touch another user's data, tokens or settings.

### Workflow
1. Specs live in `agenthub-frontend/e2e/`, config in `agenthub-frontend/playwright.config.ts` (create them if absent; `baseURL` comes from `E2E_BASE_URL`, default `https://www.4genthub.com`). Tell the lead which spec files you create so web-dev does not edit them.
2. Run one spec at a time with `npx playwright test <file> --workers=1`. Never start the UI mode or a watch mode. First run: `npx playwright install chromium` if the browser is missing.
3. First spec: log in, land on the dashboard, open Topology and Sessions, log out. Assert on visible text and roles, not on CSS classes.
4. A failure is a finding only after you ran it twice and read the trace. Report: the page, the step, expected, actual, the command. Say which results you saw and which you inferred.

### Do not
Report a visual result you did not see. Commit a credential. Run against any host other than `www.4genthub.com` without the lead's word. Retry a login more than twice: a wrong password locks the account.
