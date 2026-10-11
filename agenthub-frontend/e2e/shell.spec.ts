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

const WIDTHS = [768, 1023, 1280, 1440] as const
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
  /**
   * The profile trigger's text, read twice: as the DOM holds it, and as the browser
   * RENDERS it. In 768-1023 the name/email block is still in the DOM and paints
   * nothing, so the two differ; from 1024 nothing yields and they are equal. Reading
   * only the DOM text cannot see the yield at all, and reading a neighbour is worse:
   * the first version of this field took the first button in the right group, which
   * is the WebSocket status, so it reported "Connected" at every width.
   */
  profileText: string
  profileTextRendered: string
  /** Controls inside the visible navigation: the tablet band's eight links plus its theme toggle. */
  navControls: number
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

    const right = header?.querySelectorAll(':scope > div > *')[1]
    // The profile trigger is the LAST button in the right group, not the first: the
    // first is the WebSocket status, and reading that one is exactly how the yield
    // rule passed at 768 for the wrong reason ("Connected", 9 characters, at every
    // width). The dropdown's own menu can render in this subtree too, so the trigger
    // is named by its position in the row's DOM order - status, bell, glow nav, tablet
    // nav, mobile button, profile - and read from its button, not from the wrapper.
    const rightButtons = Array.from(right?.querySelectorAll('button') ?? [])
    const profileTrigger = rightButtons[rightButtons.length - 1] ?? null
    const rendered = (el: Element | null): string =>
      ((el as HTMLElement | null)?.innerText ?? '').replace(/\s+/g, ' ').trim()

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
      rightPieces: right
        ? Array.from(right.children).map((el) => ({
            name: pieceName(el),
            width: box(el).width,
          }))
        : [],
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
      profileText: (profileTrigger?.textContent ?? '').replace(/\s+/g, ' ').trim(),
      profileTextRendered: rendered(profileTrigger),
      navControls: nav ? nav.querySelectorAll('a, button').length : 0,
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

  // WHICH BUTTON IS THE THEME CONTROL DEPENDS ON THE WIDTH, and the one that comes
  // first in the DOM is not it in the band. The glow menu's toggle (text, its
  // rotated back face makes the accessible name "Dark Dark") is inside
  // `div.hidden.lg:block`; the tablet strip's is icon-only and carries its mode in
  // `title` (`Header.tsx:190-196`). Taking `.first()` of a text filter therefore
  // bound to the glow toggle at 768 - present, never visible - and the click waited
  // for an element that cannot become actionable, which is a test timeout and not a
  // finding. Match the VISIBLE control of either band, by text or by title.
  const mode = want === 'dark' ? 'Dark' : 'Light'
  await page
    .locator(
      `header nav button:has-text("${mode}"):visible, header nav button[title="${mode} Mode"]:visible`,
    )
    .first()
    .click()

  await expect
    .poll(isDark, { message: `the header's theme control switched to ${want}` })
    .toBe(want === 'dark')
}

test('the shell: one-line nav, one h1, one accent, both themes', async ({ page }) => {
  // Four viewports, two themes each, two screenshots per reading, so the total needs
  // more than the default 60s - but a single hung action must not eat the ceiling and
  // report only "timed out", which is how the band first surfaced a click that could
  // never succeed. One action gets 15s; the run gets 180s.
  page.setDefaultTimeout(15_000)
  test.setTimeout(180_000)
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

      // PROTECTED STRUCTURE, asserted as structure and not only as fit: the band
      // yields redundancy (the profile's name and email), never identity or reach.
      // These pin the wordmark and the tablet navigation's controls so a later change
      // cannot "fix" the band by deleting the brand or a destination.
      await expect(
        page.locator('header').getByText('4genthub'),
        `${width}px: the brand survives in the band`,
      ).toBeVisible()
      if (width < 1024) {
        expect(
          reading.navControls,
          `${width}px: the tablet navigation keeps eight destinations plus the theme toggle`,
        ).toBe(9)
      }

      // THE YIELD RULE, asserted as a rule rather than as "the text is gone". The
      // instrument is the profile trigger's own button read twice: as the DOM holds it
      // and as the browser RENDERS it. The comparison strips whitespace from both,
      // because innerText inserts a separator between block children (avatar, name,
      // email) where textContent has none - the raw strings measured 23 against 21 at
      // 1280 with nothing yielding. The account's own strings are deliberately not
      // used: they stay inside the test process, and a pass that depended on them would
      // pass for the wrong reason the moment the login and the displayed name differ.
      // Only LENGTHS are printed, never the text the trigger renders.
      const dom = reading.profileText.replace(/\s+/g, '')
      const shown = reading.profileTextRendered.replace(/\s+/g, '')
      if (width < 1024) {
        // The avatar's initials must still render - a deleted trigger is not a yield -
        // and the name and email must not. The measured shape is 1 character of 21.
        expect(
          shown.length > 0 && shown.length < dom.length,
          `${width}px: the profile trigger renders the avatar alone (${shown.length} rendered of ${dom.length} DOM chars)`,
        ).toBe(true)
      } else {
        expect(
          shown === dom,
          `${width}px: the profile trigger renders its name and email (${shown.length} rendered of ${dom.length} DOM chars)`,
        ).toBe(true)
      }

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
          `hues=${JSON.stringify(reading.navHues)} sources=${JSON.stringify(reading.hueSource)} ` +
          // The yield rule's instrument, printed as two LENGTHS - rendered against
          // DOM. A failing run then says whether the block was in the DOM but
          // unpainted (the yield) or absent altogether (a deletion, which this rule
          // must not accept as a pass).
          `profile=${reading.profileTextRendered.length}rendered/${reading.profileText.length}domChars ` +
          `navControls=${reading.navControls}`,
      )

      await page.locator('header').screenshot({ path: path.join(OUT, `header-${width}-${theme}.png`) })
      await page.screenshot({ path: path.join(OUT, `page-${width}-${theme}.png`) })
    }
  }

  for (const reading of readings) {
    const where = `${reading.width}px ${reading.theme}`

    // 1. The glow navigation is one line and fits. It renders from 1024 up, and the
    // band at 768-1023 shows the tablet icon strip instead: those items carry no
    // text labels, so there is no line box or pill geometry to measure there. The
    // tablet strip's own structure (eight destinations plus the theme toggle) and its
    // fit are asserted from its reading in the loop above, not by weakening these.
    if (reading.width >= 1024) {
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
    }
    expect(
      reading.doc.scrollWidth,
      `${where}: the chrome does not make the document scroll sideways`,
    ).toBeLessThanOrEqual(reading.doc.innerWidth + 1)
    expect(reading.headerHeight, `${where}: chrome height`).toBeLessThanOrEqual(80)
    // The band's own instrument: the header must fit its CONTENT BOX, which is the
    // pair that names the header as the overflowing element rather than the page (at
    // 768 the box is 720px, because px-6 leaves 48, and the ruling measured a 92px
    // deficit against it). This is a real fit, not the parity bound A3 first carried:
    // the profile's name/email yield is what makes it attainable.
    expect(
      reading.headerBox.scrollWidth,
      `${where}: the header's own content fits its box (${reading.headerBox.scrollWidth}/${reading.headerBox.clientWidth})`,
    ).toBeLessThanOrEqual(reading.headerBox.clientWidth)

    // 2. The page's own title is the only h1.
    expect(reading.h1s, `${where}: the page's h1 elements`).toEqual([TITLE])

    // 3. One accent colour in the navigation, and it is this theme's token. This is
    // the GLOW navigation's promise (the eight per-item hues F-5 retired), so it is
    // asserted where that navigation renders - from 1024 up. In the band the walk
    // collects an empty set, which is a fact about the tablet strip, not a rule.
    if (reading.width >= 1024) {
      expect(reading.navHues, `${where}: accent colours painted by the navigation`).toHaveLength(1)
      expect(reading.navHues[0], `${where}: the navigation's accent is --accent`).toBe(
        cssRgb(reading.accent),
      )
    }
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

// R1 (theme): the login button is painted from the one accent token. Read SIGNED
// OUT, so no credential is involved and no login is attempted for a colour.
test('R1: the login button paints --color-accent, signed out', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/login')

  const button = page.getByRole('button', { name: 'Sign In' }).first()
  await expect(button).toBeVisible()

  const painted = await button.evaluate((el) => getComputedStyle(el).backgroundColor)
  const reading = await page.evaluate(() => ({
    accent: getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim(),
    dark: document.documentElement.classList.contains('dark'),
  }))
  console.log(`R1 reading: button=${painted} accent=${reading.accent} dark=${reading.dark}`)

  // MUI's contained override names the light palette's button colour, so this is a
  // light-mode reading; a surprise in the mode fails here rather than as a hue
  // mismatch that looks like a palette bug.
  expect(reading.dark, 'the login page is read in the default light theme').toBe(false)
  expect(reading.accent, 'the token layer declares --color-accent').toBeTruthy()
  expect(painted, 'the Sign In button is painted from --color-accent').toBe(cssRgb(reading.accent))
})

// R2 (shell): the mobile drawer's `top` is the header's own measured height, not a
// declared token. Before this the drawer offset itself by --shell-header-h (56px)
// while the header is 73px at this width, so the menu started 17px too high.
test('R2: the mobile drawer starts where the header ends', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await signIn(page)
  await page.goto(TITLE_ROUTE)

  const readTop = () =>
    page.evaluate(() => {
      const header = document.querySelector('header')
      const drawer = Array.from(document.querySelectorAll('div')).find(
        (d) =>
          d.className.includes('fixed left-0 right-0') && d.className.includes('md:hidden'),
      )
      return {
        header: header ? Math.round(header.getBoundingClientRect().height) : -1,
        drawer: drawer ? Math.round(drawer.getBoundingClientRect().top) : -1,
      }
    })

  await page.getByRole('button', { name: 'Toggle mobile menu' }).click()
  // The drawer slides in (`animate-slide-in`), so a rect read straight after the
  // click reports the animation's own offset, not the resting top: a first run read
  // 64px under a 73px header for exactly that reason. Settle, as the shell test does.
  await page.waitForTimeout(500)
  const opened = await readTop()
  console.log(`R2 reading: header=${opened.header}px drawerTop=${opened.drawer}px`)
  expect(opened.drawer, 'the drawer is on screen').toBeGreaterThan(0)
  expect(opened.drawer, 'the drawer starts at the header height').toBe(opened.header)

  // The measured value is re-read on resize, which is the other half of the fix.
  await page.setViewportSize({ width: 500, height: 844 })
  await page.waitForTimeout(200)
  const resized = await readTop()
  console.log(`R2 reading after resize: header=${resized.header}px drawerTop=${resized.drawer}px`)
  expect(resized.drawer, 'still flush after a resize').toBe(resized.header)
})

// A3 (shell): the sub-label yields from md up. The band then fits for real - the
// strict `<= innerWidth + 1` assertion above now runs at 768 and 1023 as well, and
// the architect's band ruling of 2026-10-11 is what made that attainable by yielding
// the profile's name/email block. The earlier caution ("do not extend the strict
// assertion to 768, the baseline fails it" - the pre-fix reading was 860/768) is
// therefore superseded by the fix, not ignored: parity was the state before the yield,
// a fit is the state after it.
const MD_WIDTHS = [768, 900, 1023] as const

test('A3: the sub-label yields from md, and the tablet band fits', async ({ page }) => {
  await signIn(page)

  for (const width of MD_WIDTHS) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto(TITLE_ROUTE)
    await expect(page.getByRole('heading', { name: TITLE, level: 1 })).toBeVisible()

    await expect(
      page.getByText('AI Orchestration Platform'),
      `${width}px: the sub-label is hidden from md up`,
    ).toBeHidden()

    const reading = await readShell(page, width)
    console.log(
      `A3 reading ${width}px: doc=${reading.doc.scrollWidth}/${reading.doc.innerWidth} ` +
        `headerRow=${JSON.stringify(reading.headerRow)} ` +
        `pieces=${JSON.stringify(reading.headerPieces)}`,
    )
    expect(
      reading.doc.scrollWidth,
      `${width}px: the band fits (${reading.doc.scrollWidth}/${reading.doc.innerWidth})`,
    ).toBeLessThanOrEqual(reading.doc.innerWidth + 1)
  }
})
