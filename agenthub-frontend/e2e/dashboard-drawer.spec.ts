import { test, expect, type Page } from '@playwright/test'

import { readTestAccount } from './account'

// Read once, inside the test process. Never logged, never titled, never attached.
const account = readTestAccount()

/**
 * The dashboard drawer, on the phone.
 *
 * Task 6e84d62e: the drawer put the project row actions at right=419 with hover-only visibility
 * (`opacity-0 group-hover:opacity-100`), so a touch user could not reach Eye/Create Branch/Edit/
 * Delete, and the rows overflowed a 375px drawer. The phone walk (e2e/phone-layout.spec.ts) did not
 * catch the branch rows because it never expands a project, so those two actions stayed at 24x24.
 *
 * This spec is that missing proof, as a command: at 375x667 and 320x568, mobile emulation, no hover
 * anywhere, the drawer is opened through its toggle, the first project is expanded, and every
 * VISIBLE row action is measured - opacity, both sides of its box, and its right edge against the
 * viewport. Tapping View Branch Details must open a dialog, which is what "clickable" means here.
 *
 * Nothing asserts a class string or a colour. Readiness is the app's own data: the drawer renders
 * only after the project tree arrives, so the spec waits for a row action to exist in the aside.
 */

async function signIn(page: Page): Promise<void> {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()
  await page.getByRole('textbox', { name: 'Email Address' }).fill(account.username)
  await page.getByRole('textbox', { name: 'Password' }).fill(account.password)
  await page.getByRole('button', { name: 'Sign In' }).click()
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 45_000 })
}

/** The drawer toggle is the phone's only route to the project tree. */
const TOGGLE = 'button.fixed.bottom-6.left-6'

/**
 * The actions a project row and a branch row carry. Delete Branch is rendered only for a branch
 * that is not `main` (BranchItem), so it is optional here: when the tree has no other branch it is
 * correctly absent, and when it is present it must pass the same measurement. Required means the
 * action exists in the drawer at all - the project four and View Branch Details are unconditional.
 */
const REQUIRED_ACTIONS = [
  'View Project Details',
  'Create Branch',
  'Edit',
  'Delete',
  'View Branch Details',
] as const

const OPTIONAL_ACTIONS = ['Delete Branch'] as const

const ACTIONS = [...REQUIRED_ACTIONS, ...OPTIONAL_ACTIONS] as const

const FLOOR = 40

interface ActionBox {
  width: number
  height: number
  right: number
  opacity: string
  visibility: string
}

function measureInPage(labels: readonly string[]) {
  const aside = document.querySelector('aside')
  if (!aside) throw new Error('no <aside> on the page')

  const box = (el: Element): ActionBox => {
    const r = el.getBoundingClientRect()
    const style = getComputedStyle(el)
    return {
      width: Math.round(r.width * 100) / 100,
      height: Math.round(r.height * 100) / 100,
      right: Math.round(r.right * 100) / 100,
      opacity: style.opacity,
      visibility: style.visibility,
    }
  }

  const actions: Record<string, ActionBox[]> = {}
  for (const label of labels) {
    actions[label] = [...aside.querySelectorAll(`button[aria-label="${label}"]`)].map(box)
  }

  // A row that does not fit shows up as an element whose right edge passes the viewport's.
  const overflowing = [...aside.querySelectorAll('*')]
    .filter((el) => {
      const r = el.getBoundingClientRect()
      return r.width > 0 && r.height > 0 && r.right > window.innerWidth + 0.5
    })
    .map((el) => `${el.tagName.toLowerCase()}.${(typeof el.className === 'string' ? el.className : '').split(/\s+/).slice(0, 3).join('.')}`)

  return { actions, overflowing, innerWidth: window.innerWidth }
}

for (const [width, height] of [
  [375, 667],
  [320, 568],
] as const) {
  test.describe(`dashboard drawer ${width}x${height}`, () => {
    test.use({ viewport: { width, height }, isMobile: true, hasTouch: true, deviceScaleFactor: 1 })

    test.beforeEach(async ({ page }) => {
      await signIn(page)
    })

    test(`row actions are reachable without hover and the rows fit ${width}px`, async ({ page }) => {
      await page.goto('/dashboard')
      await expect(page.getByRole('main').first()).toBeVisible()
      await expect
        .poll(async () => (await page.getByRole('main').first().innerText()).trim().length, { timeout: 30_000 })
        .toBeGreaterThan(60)

      await page.locator(TOGGLE).click()
      const aside = page.locator('aside')
      await expect(aside).toBeVisible()

      // The project tree arrives with the dashboard's data: wait for a row action, not a timer.
      await expect
        .poll(async () => aside.locator('button[aria-label="View Project Details"]').count(), { timeout: 30_000 })
        .toBeGreaterThan(0)

      // Expanding is what makes the branch rows render at all - the phone walk's blind spot.
      const chevron = aside.locator('.lucide-chevron-right').first()
      await expect(chevron).toBeVisible()
      await chevron.locator('xpath=..').click()
      await expect
        .poll(async () => aside.locator('button[aria-label="View Branch Details"]').count(), { timeout: 30_000 })
        .toBeGreaterThan(0)
      await page.waitForTimeout(400) // the expand animation, not data

      // Tapping the branch action must open its dialog: a control that is visible but inert fails here.
      await aside.locator('button[aria-label="View Branch Details"]').first().click()
      await expect(page.locator('[role=dialog]').first()).toBeVisible({ timeout: 10_000 })
      await page.keyboard.press('Escape')
      await expect(page.locator('[role=dialog]')).toHaveCount(0, { timeout: 10_000 })

      const m = await page.evaluate(measureInPage, ACTIONS)

      const problems: string[] = []

      for (const label of ACTIONS) {
        const visible = m.actions[label].filter((b) => b.width > 0 && b.height > 0)
        if (visible.length === 0) {
          if ((REQUIRED_ACTIONS as readonly string[]).includes(label)) {
            // Every required action must be reachable at both widths: the drawer is the phone's only route to it.
            problems.push(`${label}: no visible button in the open drawer`)
          }
          continue
        }
        for (const b of visible) {
          if (b.width < FLOOR - 0.01 || b.height < FLOOR - 0.01) {
            problems.push(`${label}: ${b.width}x${b.height} under the ${FLOOR}x${FLOOR} floor`)
          }
          if (Number(b.opacity) < 1) {
            problems.push(`${label}: opacity ${b.opacity} with no hover, so a touch user cannot see it`)
          }
          if (b.right > m.innerWidth + 0.5) {
            problems.push(`${label}: right edge ${b.right} past the ${m.innerWidth}px viewport`)
          }
        }
      }

      for (const el of m.overflowing) problems.push(`aside element past the viewport: ${el}`)

      expect(problems, `drawer at ${width}x${height}`).toEqual([])
    })
  })
}
