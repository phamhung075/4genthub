import { test, expect, type Page } from '@playwright/test'

import { readTestAccount } from './account'

// Read once, inside the test process. Never logged, never titled, never attached.
const account = readTestAccount()

/**
 * The deploy smoke: sign in, land on the dashboard, open Topology and Sessions,
 * sign out.
 *
 * It asserts on what a user sees - headings, roles, the two states the sessions
 * list can be in - and not on CSS classes or on an element that only exists when
 * the data happens to be there. A screen with neither rows nor the empty state is
 * a failure, which is why the sessions check accepts either and nothing else.
 */
async function signIn(page: Page): Promise<void> {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()

  // Roles, not labels: the MUI label carries a required asterisk, so an exact
  // label match misses, and the password field also has a toggle button whose
  // accessible name contains the same word.
  await page.getByRole('textbox', { name: 'Email Address' }).fill(account.username)
  await page.getByRole('textbox', { name: 'Password' }).fill(account.password)
  await page.getByRole('button', { name: 'Sign In' }).click()

  // The redirect is the session's proof: /dashboard is behind ProtectedRoute.
  await expect(page).toHaveURL(/\/dashboard/, { timeout: 45_000 })
}

async function signOut(page: Page): Promise<void> {
  // The banner's profile trigger is the button carrying the account's identity
  // (initials, name, email); Sign Out lives in its menu (UserProfileDropdown).
  await page.getByRole('banner').getByRole('button', { name: /@/ }).click()
  await page.getByText('Sign Out').click()

  await expect(page).toHaveURL(/\/login/)
}

test('a signed-in user reaches the dashboard, Topology and Sessions, then signs out', async ({ page }) => {
  await signIn(page)

  await page.goto('/topology')
  await expect(page.getByRole('heading', { name: 'Topology' })).toBeVisible()

  await page.goto('/sessions')
  await expect(page.getByRole('heading', { name: 'Sessions' })).toBeVisible()

  // Scoped to main: the sidebar is a list too, so an unscoped role=list is two
  // elements under a strict locator. Either state is a rendered surface - rows,
  // or the empty state that says what registers sessions - and a screen with
  // neither is the failure this asserts against.
  const main = page.getByRole('main')
  await expect(main.getByText(/No sessions yet/).or(main.getByRole('listitem').first())).toBeVisible()

  await signOut(page)
})
