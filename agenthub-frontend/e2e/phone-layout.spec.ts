import { test, expect, type Page, type Request } from '@playwright/test'

import { readTestAccount } from './account'

// Read once, inside the test process. Never logged, never titled, never attached.
const account = readTestAccount()

/**
 * The phone walk, on the repo harness.
 *
 * Ruling: seats/architect/RULING-phone-walk-home-2026-10-18.md. The ten signed-in routes are
 * measured at 375x667 and 320x568, and one touch rule runs over the same pages: an icon button -
 * a button or [role=button] with no non-whitespace text, so the glyph is the whole hit area - has
 * a border box of at least 40x40 CSS px. Text links and inline anchors are out of scope by design.
 *
 * Each route carries three layout conditions:
 *   1. document.scrollingElement.scrollWidth === window.innerWidth (the document does not drag),
 *   2. main.scrollWidth === main.clientWidth (the scroll pane does not drag sideways),
 *   3. no element under main has its right edge past main's, unless it lives inside an ancestor
 *      whose computed overflow-x is auto or scroll - the code blocks that scroll on purpose.
 *
 * Nothing here asserts a CSS class, a colour or data-dependent content. Readiness is two things:
 * main carries the mounted route's text, and the app's /api requests have gone quiet, because the
 * pages lay out around their data - a project tree that has not arrived yet measures narrower and
 * would pass a route that really drags.
 *
 * Acceptance is a command, not a screenshot: `npx playwright test e2e/phone-layout.spec.ts`
 * from agenthub-frontend, with E2E_BASE_URL naming the origin (default: the deployed app) and
 * E2E_ACCOUNT_FILE naming the account file when the repo-root default is not there.
 */

const ROUTES = [
  '/dashboard',
  '/tokens',
  '/seats',
  '/seats/authoring',
  '/sessions',
  '/topology',
  '/profile',
  '/feedback',
  '/docs',
  '/help-setup',
]

async function signIn(page: Page): Promise<void> {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()

  // Roles, not labels: the MUI label carries a required asterisk, so an exact label match
  // misses, and the password field also has a toggle button whose accessible name contains
  // the same word.
  await page.getByRole('textbox', { name: 'Email Address' }).fill(account.username)
  await page.getByRole('textbox', { name: 'Password' }).fill(account.password)
  await page.getByRole('button', { name: 'Sign In' }).click()

  await expect(page).toHaveURL(/\/dashboard/, { timeout: 45_000 })
}

/**
 * Counts the app's in-flight /api requests and hands back a wait for them to go quiet. The
 * WebSocket is not counted: it never closes, and it is not what lays a page out.
 */
function trackApiRequests(page: Page, quietMs = 750, timeout = 30_000) {
  let inFlight = 0
  const count = (request: Request, delta: number) => {
    if (request.url().includes('/api/')) inFlight = Math.max(0, inFlight + delta)
  }

  page.on('request', (request: Request) => count(request, 1))
  page.on('requestfinished', (request: Request) => count(request, -1))
  page.on('requestfailed', (request: Request) => count(request, -1))

  return {
    async settle(): Promise<void> {
      const deadline = Date.now() + timeout
      let quietSince: number | null = null
      while (Date.now() < deadline) {
        if (inFlight === 0) {
          quietSince ??= Date.now()
          if (Date.now() - quietSince >= quietMs) return
        } else {
          quietSince = null
        }
        await page.waitForTimeout(100)
      }
      throw new Error(`the app's /api requests did not go quiet within ${timeout}ms`)
    },
  }
}

/**
 * The page's own measurement, read in one evaluate. The app is client-rendered, so `load` is not
 * readiness: the caller waits for text and for the requests to settle before this runs.
 */
function measureInPage() {
  const main = document.querySelector('main')
  if (!main) throw new Error('no <main> on the page')

  const mainBox = main.getBoundingClientRect()
  const right = mainBox.right

  const inScroller = (el: Element): boolean => {
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const ox = getComputedStyle(p).overflowX
      if (ox === 'auto' || ox === 'scroll') return true
    }
    return false
  }

  const label = (el: Element): string => {
    const cls = typeof el.className === 'string' ? el.className : ''
    const text = (el.textContent ?? '').trim().slice(0, 24)
    return (
      `${el.tagName.toLowerCase()}${cls ? '.' + cls.split(/\s+/).slice(0, 3).join('.') : ''}` +
      `${text ? ` "${text}"` : ''}${el.getAttribute('aria-label') ? ` [${el.getAttribute('aria-label')}]` : ''}`
    )
  }

  const offenders = [...main.querySelectorAll('*')]
    .filter((el) => {
      const r = el.getBoundingClientRect()
      return r.width > 0 && r.height > 0 && !inScroller(el) && r.right > right + 1
    })
    .map(label)

  const visible = (el: Element): boolean => {
    const r = el.getBoundingClientRect()
    if (r.width === 0 || r.height === 0) return false
    if (typeof el.checkVisibility === 'function') {
      return el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })
    }
    return getComputedStyle(el).visibility !== 'hidden'
  }

  const FLOOR = 40
  const smallControls = [
    ...document.querySelectorAll(
      'main button, main [role=button], header button, header [role=button], aside button, aside [role=button]',
    ),
  ]
    .filter((el) => visible(el) && (el.textContent ?? '').trim() === '')
    .map((el) => {
      const r = el.getBoundingClientRect()
      return {
        what: label(el),
        width: Math.round(r.width * 100) / 100,
        height: Math.round(r.height * 100) / 100,
      }
    })
    .filter((c) => c.width < FLOOR - 0.01 || c.height < FLOOR - 0.01)

  return {
    documentScrollWidth: document.scrollingElement?.scrollWidth ?? -1,
    innerWidth: window.innerWidth,
    mainScrollWidth: main.scrollWidth,
    mainClientWidth: main.clientWidth,
    mainRight: right,
    offenders,
    smallControls,
  }
}

for (const [width, height] of [
  [375, 667],
  [320, 568],
] as const) {
  test.describe(`phone layout ${width}x${height}`, () => {
    test.use({ viewport: { width, height }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 })

    test.beforeEach(async ({ page }) => {
      await signIn(page)
    })

    for (const route of ROUTES) {
      test(`${route} fits ${width}px and meets the 40px floor`, async ({ page }) => {
        const api = trackApiRequests(page)
        await page.goto(route)
        await expect(page.getByRole('main').first()).toBeVisible()

        // Mounted: /dashboard renders 106 characters in main, the smallest real page, while a
        // shell that never mounted has 0. A page that fails to mount fails here with the route
        // named instead of passing every layout check over nothing.
        await expect
          .poll(async () => (await page.getByRole('main').first().innerText()).trim().length, { timeout: 30_000 })
          .toBeGreaterThan(60)

        await api.settle()

        const m = await page.evaluate(measureInPage)

        // Every violation is reported, not just the first: a re-walk after a deploy should say
        // the whole state of the route in one failure.
        const problems: string[] = []
        if (m.documentScrollWidth !== m.innerWidth) {
          problems.push(`document ${m.documentScrollWidth}px wide in a ${m.innerWidth}px viewport`)
        }
        if (m.mainScrollWidth !== m.mainClientWidth) {
          problems.push(`main scrolls ${m.mainScrollWidth}px wide inside ${m.mainClientWidth}px`)
        }
        for (const offender of m.offenders) problems.push(`right edge past main (${m.mainRight}px): ${offender}`)
        for (const control of m.smallControls) {
          problems.push(`icon button ${control.width}x${control.height} under the 40x40 floor: ${control.what}`)
        }

        expect(problems, `${route} at ${width}x${height}`).toEqual([])
      })
    }
  })
}
