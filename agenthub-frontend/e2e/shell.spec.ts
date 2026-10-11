import fs from 'node:fs'
import path from 'node:path'

import { test, expect, type Page } from '@playwright/test'

import { readTestAccount } from './account'

// Read once, inside the test process. Never logged, never titled, never attached.
const account = readTestAccount()

/**
 * The app shell + token layer slice's acceptance spec (fe-dev).
 *
 * It measures the four promises that slice makes, on the chrome every signed-in
 * page sits in, and writes the before/after screenshot pair the plan asks for:
 *
 *   1. the navigation is one line, and fits, at 1280 and 1440
 *   2. the page's own title is the only `<h1>` on the page
 *   3. the navigation paints one accent colour, and it is the theme's `--accent`
 *   4. both themes were looked at, not assumed
 *
 * WHERE IT POINTS: `E2E_BASE_URL` (playwright.config.ts) defaults to the deployed
 * app. A slice's before/after pair points it at the local dev server, whose /api
 * rides the proxy in vite.config.ts, so the same spec measures the same source
 * before and after the change.
 *
 * WHY THE ACCENT IS MEASURED BY WALKING THE NAV: the finding (F-5) is that the
 * header ships eight per-item hues at once, so the instrument collects what the
 * navigation actually paints - icon colours and the glow layer behind each item -
 * and compares that set with the theme's own `--accent`. No hex value is pinned
 * here: retuning the token keeps this green, a second hue turns it red, and the
 * reported set names the offending colour instead of just failing.
 *
 * THE TWO THINGS IT DELIBERATELY DOES NOT MEASURE: the status indicators
 * (WebSocketStatus, NotificationBell) and the wordmark's sparkles are outside the
 * navigation subtree, so their status and brand hues are not counted as accents -
 * the token layer's own rule is that status colours are status-only.
 */

const OUT = process.env.E2E_SHELL_OUT ?? path.resolve(__dirname, '..', 'audit-runs', 'shell')

const WIDTHS = [1280, 1440] as const
const TITLE = 'Seats'
const TITLE_ROUTE = '/seats'

/** `#4f46e5` -> `rgb(79, 70, 229)`, the form Chrome's computed styles use. */
function cssRgb(hex: string): string {
  const value = hex.replace('#', '').trim()
  const full = value.length === 3 ? value.split('').map((c) => c + c).join('') : value
  const int = parseInt(full, 16)
  return `rgb(${(int >> 16) & 255}, ${(int >> 8) & 255}, ${int & 255})`
}

async function signIn(page: Page): Promise<void> {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()

  // Roles, not labels: the MUI label carries a required asterisk and the password
  // field's own toggle button repeats the word.
  await page.getByRole('textbox', { name: 'Email Address' }).fill(account.username)
  await page.getByRole('textbox', { name: 'Password' }).fill(account.password)
  await page.getByRole('button', { name: 'Sign In' }).click()

  await expect(page).toHaveURL(/\/dashboard/, { timeout: 45_000 })
}

type NavItem = {
  label: string
  labelRects: number
  top: number
  left: number
  right: number
  height: number
}

type ShellReading = {
  width: number
  theme: string
  accent: string
  headerHeight: number
  /** The header's row, the pieces inside it, and the right group's own children. */
  headerRow: { name: string; width: number }[]
  headerPieces: { name: string; width: number; height: number }[]
  rightPieces: { name: string; width: number }[]
  /** The header's own box: attribution for a document that scrolls sideways. */
  headerBox: { scrollWidth: number; clientWidth: number }
  navTextActive: string
  htmlInlineStyle: boolean
  nav: { found: boolean; scrollWidth: number; clientWidth: number; left: number; right: number }
  ul: { scrollWidth: number; clientWidth: number }
  doc: { scrollWidth: number; innerWidth: number }
  items: NavItem[]
  h1s: string[]
  navHues: string[]
  hueSource: Record<string, string>
}

/**
 * One page read: what the shell looks like at this width and theme, as numbers.
 * Everything is computed in the page, so the assertion messages can print the
 * measurement (a colour set, a rect count) rather than only saying it failed.
 */
async function readShell(page: Page, width: number): Promise<ShellReading> {
  return page.evaluate((width: number): ShellReading => {
    const root = document.documentElement
    // The token layer's role names live under `--color-*`: the bare `--accent`,
    // `--bg`, `--border` and `--text` names already belong to the shadcn/ui layer
    // that ships in this app, and overwriting them would restyle every shadcn
    // component instead of stating the product's own roles.
    const accent = getComputedStyle(root).getPropertyValue('--color-accent').trim()

    const header = document.querySelector('header')
    const headerHeight = header ? Math.round(header.getBoundingClientRect().height) : 0

    // The navigation on screen: at >=1024px the glow menu renders and the tablet
    // and mobile ones are display:none, whose rects measure 0.
    const navs = Array.from(document.querySelectorAll('header nav')).filter(
      (n) => n.getBoundingClientRect().width > 0,
    )
    const nav = navs[0]

    const items: NavItem[] = []
    if (nav) {
      // A wrapped label is a second line box. The label span is a flex item, and a
      // blockified flex item reports ONE rect however many lines its text wraps to,
      // so the line boxes are counted with a range over its contents instead.
      const lineBoxes = (el: Element): number => {
        const range = document.createRange()
        range.selectNodeContents(el)
        return range.getClientRects().length
      }

      for (const li of Array.from(nav.querySelectorAll('li'))) {
        const labelSpans = Array.from(li.querySelectorAll('span')).filter((s) =>
          s.classList.contains('text-sm'),
        )
        if (labelSpans.length === 0) continue
        const label = labelSpans[0].textContent?.trim() ?? ''
        const rect = li.getBoundingClientRect()
        items.push({
          label,
          labelRects: Math.max(...labelSpans.map(lineBoxes)),
          top: Math.round(rect.top),
          left: Math.round(rect.left),
          right: Math.round(rect.right),
          height: Math.round(rect.height),
        })
      }
    }

    // Everything the navigation paints: computed colours, and every colour inside
    // a background-image string (the per-item glow gradients live there). Each hue
    // also records the element that painted it, so an unexpected colour in a
    // failing run names its own source instead of only its value.
    const hues = new Set<string>()
    const hueSource: Record<string, string> = {}
    const collect = (raw: string, el: Element): void => {
      for (const token of raw.match(/rgba?\([^)]+\)/g) ?? []) {
        const parts = token.match(/[\d.]+/g)?.map(Number) ?? []
        const [r, g, b] = parts
        const alpha = parts.length > 3 ? parts[3] : 1
        if (alpha <= 0.1) continue
        // Near-greys are the text, border and surface tokens (slate-400, the
        // tightest of them, spans 36 across its channels); every accent this design
        // uses is far above 60, so the spread separates them.
        if (Math.max(r, g, b) - Math.min(r, g, b) < 60) continue
        const rgb = `rgb(${r}, ${g}, ${b})`
        hues.add(rgb)
        if (!hueSource[rgb]) {
          const classes = String(el.getAttribute('class') ?? '')
            .split(/\s+/)
            .slice(0, 3)
            .join('.')
          hueSource[rgb] = `${el.tagName.toLowerCase()}${classes ? `.${classes}` : ''}`
        }
      }
    }

    if (nav) {
      for (const el of [nav, ...Array.from(nav.querySelectorAll('*'))]) {
        const style = getComputedStyle(el)
        collect(style.color, el)
        collect(style.backgroundColor, el)
        collect(style.backgroundImage, el)
        collect(style.borderTopColor, el)
        collect(style.stroke, el)
        collect(style.fill, el)
      }
    }

    const ul = nav?.querySelector('ul') ?? null

    const pieceName = (el: Element): string =>
      `${el.tagName.toLowerCase()}.${String(el.getAttribute('class') ?? '')
        .split(/\s+/)
        .slice(0, 3)
        .join('.')}`
    const box = (el: Element): { width: number; height: number } => {
      const rect = el.getBoundingClientRect()
      return { width: Math.round(rect.width), height: Math.round(rect.height) }
    }

    return {
      width,
      theme: root.classList.contains('dark') ? 'dark' : 'light',
      accent,
      headerHeight,
      headerRow: header
        ? Array.from(header.children).map((el) => ({ name: pieceName(el), width: box(el).width }))
        : [],
      headerPieces: Array.from(header?.querySelectorAll(':scope > div > *') ?? []).map((el) => ({
        name: pieceName(el),
        ...box(el),
      })),
      rightPieces: (() => {
        const right = header?.querySelectorAll(':scope > div > *')[1]
        return right
          ? Array.from(right.children).map((el) => ({
              name: pieceName(el),
              width: box(el).width,
            }))
          : []
      })(),
      nav: nav
        ? {
            found: true,
            scrollWidth: nav.scrollWidth,
            clientWidth: nav.clientWidth,
            left: Math.round(nav.getBoundingClientRect().left),
            right: Math.round(nav.getBoundingClientRect().right),
          }
        : { found: false, scrollWidth: 0, clientWidth: 0, left: 0, right: 0 },
      headerBox: header
        ? { scrollWidth: header.scrollWidth, clientWidth: header.clientWidth }
        : { scrollWidth: 0, clientWidth: 0 },
      navTextActive: getComputedStyle(root).getPropertyValue('--color-nav-text-active').trim(),
      // The token layer's comment says these variables are also updated from
      // JavaScript; an inline style on <html> is how that would show itself, and it
      // would silently outrank every declaration in theme.css.
      htmlInlineStyle: Boolean(root.getAttribute('style')),
      // Kept for the record only. Both the navigation and its list report their
      // scrollWidth a few px over their clientWidth REGARDLESS of content (751/748
      // before the rows were narrowed, 735/732 after), and the nav's 4px is its
      // decorative -inset-1 layer by design, so this ratio cannot decide whether the
      // pills fit; the item edges, asserted against the nav's own box, are the
      // honest instrument.
      ul: ul
        ? { scrollWidth: ul.scrollWidth, clientWidth: ul.clientWidth }
        : { scrollWidth: 0, clientWidth: 0 },
      doc: {
        scrollWidth: document.documentElement.scrollWidth,
        innerWidth: window.innerWidth,
      },
      items,
      h1s: Array.from(document.querySelectorAll('h1')).map((h) => h.textContent?.trim() ?? ''),
      navHues: Array.from(hues).sort(),
      hueSource,
    }
  }, width)
}

/**
 * Drives the product's own theme control (the glow menu item labelled Dark or
 * Light) rather than setting a class behind the app's back. The label is matched
 * on text and not exactly: the glow menu paints each item twice - a front face and
 * a rotated back face for the hover flip - so the button's accessible name is
 * "Dark Dark", which an exact match never sees.
 */
async function ensureTheme(page: Page, want: 'light' | 'dark'): Promise<void> {
  const isDark = (): Promise<boolean> =>
    page.locator('html').evaluate((el) => el.classList.contains('dark'))

  if ((await isDark()) === (want === 'dark')) return

  await page
    .locator('header nav button')
    .filter({ hasText: want === 'dark' ? 'Dark' : 'Light' })
    .first()
    .click()

  await expect
    .poll(isDark, { message: `the header's theme control switched to ${want}` })
    .toBe(want === 'dark')
}

test('the shell: one-line nav, one h1, one accent, both themes', async ({ page }) => {
  await signIn(page)
  fs.mkdirSync(OUT, { recursive: true })

  // Everything is measured and printed BEFORE anything is asserted: a failing run
  // has to report the whole shell it saw, not the first thing that failed. The
  // instrument follows the audit's own shape (`assertClean` prints its table and
  // then fails) so a red run is still evidence.
  const readings: ShellReading[] = []

  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(TITLE_ROUTE)
    // The page's own title is present in the shell before and after the change, so
    // this wait does not depend on the assertion below it.
    await expect(page.getByRole('heading', { name: TITLE, level: 1 })).toBeVisible()

    for (const theme of ['light', 'dark'] as const) {
      await ensureTheme(page, theme)
      // The chrome animates its colours (300ms on the nav items, the motion token
      // on the shell), so a reading taken mid-flight reports a blend of the old and
      // the new colour rather than either. Settle first; a race here would show up
      // as a phantom hue that no source line can explain.
      await page.waitForTimeout(500)

      const reading = await readShell(page, width)
      readings.push(reading)
      // Printed as it is taken, not after the loop: a run that dies half way
      // through still reports every shell it did measure.
      const tops = reading.items.map((i) => i.top)
      console.log(
        `shell reading ${reading.width}px ${reading.theme}: header=${reading.headerHeight}px ` +
          `children=${JSON.stringify(reading.headerPieces)} ` +
          `row=${JSON.stringify(reading.headerRow)} right=${JSON.stringify(reading.rightPieces)} ` +
          `headerBox=${reading.headerBox.scrollWidth}/${reading.headerBox.clientWidth} ` +
          `navActive=${reading.navTextActive} htmlInlineStyle=${reading.htmlInlineStyle} ` +
          `nav=${reading.nav.scrollWidth}/${reading.nav.clientWidth} navRight=${reading.nav.right} ` +
          `ul=${reading.ul.scrollWidth}/${reading.ul.clientWidth} ` +
          `doc=${reading.doc.scrollWidth}/${reading.doc.innerWidth} ` +
          `spread=${Math.max(...tops) - Math.min(...tops)}px ` +
          `items=${JSON.stringify(reading.items.map((i) => `${i.label}:${i.labelRects}x${i.height}`))} ` +
          `h1=${JSON.stringify(reading.h1s)} accent=${reading.accent} ` +
          `hues=${JSON.stringify(reading.navHues)} sources=${JSON.stringify(reading.hueSource)}`,
      )

      await page.locator('header').screenshot({ path: path.join(OUT, `header-${width}-${theme}.png`) })
      await page.screenshot({ path: path.join(OUT, `page-${width}-${theme}.png`) })
    }
  }

  for (const reading of readings) {
    const where = `${reading.width}px ${reading.theme}`

    // 1. The navigation is one line and fits.
    expect(reading.nav.found, `${where}: the navigation is on screen`).toBe(true)
    expect(reading.items.length, `${where}: items measured`).toBeGreaterThan(5)
    for (const item of reading.items) {
      expect(
        item.labelRects,
        `${where}: "${item.label}" is ${item.labelRects} line(s), not one`,
      ).toBe(1)
    }
    const tops = reading.items.map((i) => i.top)
    const spread = Math.max(...tops) - Math.min(...tops)
    expect(spread, `${where}: every item on one row (${spread}px spread)`).toBeLessThanOrEqual(4)
    // The items must sit inside the navigation's own box: past its padding edge the
    // header clips them, and that clipping is what a user sees. A scrollWidth-over-
    // clientWidth read cannot carry this assertion - it reports the same 3px for
    // ANY content in this list (751/748 with the long labels, 735/732 after they
    // were narrowed), which is subpixel rounding, not a pill sticking out.
    const itemRights = reading.items.map((i) => i.right)
    expect(
      Math.max(...itemRights),
      `${where}: every item's right edge is inside the navigation (item rights ${JSON.stringify(
        itemRights,
      )} vs nav right ${reading.nav.right})`,
    ).toBeLessThanOrEqual(reading.nav.right + 1)
    for (let i = 1; i < reading.items.length; i += 1) {
      expect(
        reading.items[i].left,
        `${where}: "${reading.items[i].label}" starts after "${reading.items[i - 1].label}" ends (${reading.items[i].left} vs ${reading.items[i - 1].right})`,
      ).toBeGreaterThanOrEqual(reading.items[i - 1].right - 1)
    }
    expect(
      reading.doc.scrollWidth,
      `${where}: the chrome does not make the document scroll sideways`,
    ).toBeLessThanOrEqual(reading.doc.innerWidth + 1)
    expect(reading.headerHeight, `${where}: chrome height`).toBeLessThanOrEqual(80)

    // 2. The page's own title is the only h1.
    expect(reading.h1s, `${where}: the page's h1 elements`).toEqual([TITLE])

    // 3. One accent colour in the navigation, and it is this theme's token.
    expect(reading.navHues, `${where}: accent colours painted by the navigation`).toHaveLength(1)
    expect(reading.navHues[0], `${where}: the navigation's accent is --accent`).toBe(
      cssRgb(reading.accent),
    )
  }

  // 4. Both themes were looked at, and the accent token really moves between them.
  const light = readings.find((r) => r.theme === 'light')
  const dark = readings.find((r) => r.theme === 'dark')
  expect(light?.accent, 'the light theme declares --accent').toBeTruthy()
  expect(dark?.accent, 'the dark theme declares --accent').toBeTruthy()
  expect(
    dark?.accent,
    'the dark accent is the dark token, so the toggle was exercised rather than assumed',
  ).not.toBe(light?.accent)
})
