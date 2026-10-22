import fs from 'node:fs'
import path from 'node:path'

import { test, expect, type Page } from '@playwright/test'

import { readTestAccount } from './account'
import { formatChannels, parseHexColour, parsePaintedColour, sameHue } from './colour'

// Read once, inside the test process. Never logged, never titled, never attached.
const account = readTestAccount()

/**
 * The Decision Requests panel read on production (fe-dev, task c67f9ce6).
 *
 * READ-ONLY: this spec signs in, navigates and measures. It never clicks an option
 * button, "Send answer" or the lead-request Send - each is a production write - so a
 * proof that would need one is reported as `not observable` instead of taken.
 *
 * What it answers, as numbers rather than opinions:
 *  - the panel renders in the dashboard sidebar and calls that room's live decision route;
 *  - a row's text is not vertically clipped (scrollHeight vs clientHeight per element,
 *    plus what the element's own line box needs);
 *  - the room Select is not vertically clipped - the `h-10` bug the fix commit replaced
 *    with `min-h-[2.5rem] py-2 px-3 leading-normal`;
 *  - the served select-simple chunk carries that fix (class string read out of the served bytes);
 *  - no request goes to the retired /api/v2/openrig route;
 *  - the pending row's attention animation runs, and prefers-reduced-motion switches it off;
 *  - a FAILED decisions read renders its failure with the status (the failure is injected in the
 *    browser, so the request never reaches production and no server state is touched).
 *
 * The panel is mounted in the DASHBOARD's sidebar (`App.tsx`, `Dashboard()`), not on
 * `/seats/:room/:seat` - that route renders `AppLayout`, which carries no sidebar - so the
 * measured page is `/dashboard`, and the room is the one the panel's own Select shows
 * (`roomFromPath` finds no room there, so it falls back to the tenant's first room).
 *
 * Evidence goes to `test-results/room-decision-panel/` (gitignored) as JSON, never a screenshot.
 */

const ROOM = process.env.E2E_ROOM ?? '4genthub-min'
const PAGE_PATH = process.env.E2E_PAGE ?? '/dashboard'
const OUT = process.env.E2E_DECISIONS_OUT ?? path.resolve(__dirname, '..', 'test-results', 'room-decision-panel')

async function signIn(page: Page): Promise<void> {
  await page.goto('/login')
  await expect(page.getByRole('heading', { name: 'Sign In' })).toBeVisible()

  // Roles, not labels: the MUI label carries a required asterisk and the password
  // field's own toggle repeats the word.
  await page.getByRole('textbox', { name: 'Email Address' }).fill(account.username)
  await page.getByRole('textbox', { name: 'Password' }).fill(account.password)
  await page.getByRole('button', { name: 'Sign In' }).click()

  await expect(page).toHaveURL(/\/dashboard/, { timeout: 45_000 })
}

/**
 * Sign in, open the dashboard, show the room this task names and let the panel settle.
 *
 * Selecting a value in the panel's own Room dropdown is a read: it only re-issues the room's
 * decisions GET. Nothing on the page is created, changed or answered.
 */
async function openPanelForRoom(page: Page) {
  await signIn(page)
  await page.goto(PAGE_PATH)

  const panel = page.getByRole('region', { name: 'Room decision requests' })
  const panelVisible = await panel
    .waitFor({ state: 'visible', timeout: 45_000 })
    .then(() => true)
    .catch(() => false)

  const select = page.locator('select[aria-label="Room"]')
  const selectVisible = await select
    .waitFor({ state: 'visible', timeout: 30_000 })
    .then(() => true)
    .catch(() => false)

  const options = selectVisible
    ? await select.locator('option').evaluateAll((list) => list.map((option) => option.getAttribute('value')))
    : []
  const shownRoom = selectVisible ? await select.inputValue().catch(() => null) : null

  // The lead's premise names 4genthub-min; show it when the tenant's list carries it.
  const selected = selectVisible && options.includes(ROOM) && shownRoom !== ROOM
  if (selected) {
    await select.selectOption(ROOM)
    await expect(select).toHaveValue(ROOM, { timeout: 15_000 })
  }

  await page.waitForTimeout(2500)

  return { panelVisible, selectVisible, options, shownRoom, selected }
}

/** Every element of the panel's rows and the Select, measured for vertical clipping. */
function readPanelInPage() {
  const selector = '[aria-label="Room decision requests"]'

  const measure = (el: HTMLElement) => {
    const cs = getComputedStyle(el)
    const lineHeight = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2
    const needed = Math.round(lineHeight + parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom) + 2)
    const overflows = el.scrollHeight > el.clientHeight + 1
    return {
      tag: el.tagName.toLowerCase(),
      text: (el.textContent ?? '').trim().replace(/\s+/g, ' ').slice(0, 90),
      fontSize: cs.fontSize,
      lineHeight: cs.lineHeight,
      clientHeight: el.clientHeight,
      scrollHeight: el.scrollHeight,
      overflowY: cs.overflowY,
      neededHeight: needed,
      /** The shape clipping takes: content taller than the box, and the box hides it. */
      clipped: overflows && cs.overflowY !== 'visible',
      spilling: overflows && cs.overflowY === 'visible',
      /** For a control that never reports overflow (a select): shorter than its own line box. */
      shortForOwnLineBox: el.clientHeight + 1 < needed,
    }
  }

  const section = document.querySelector<HTMLElement>(selector)
  if (!section) return { found: false, panelText: '', rows: [], select: null }

  const rows = Array.from(section.querySelectorAll<HTMLElement>('article')).map((article) => ({
    state: article.querySelector('span.uppercase')?.textContent?.trim() ?? null,
    summary: (article.querySelector('span.font-medium')?.textContent ?? '').trim(),
    elements: [article, ...Array.from(article.querySelectorAll<HTMLElement>('*'))].map(measure),
  }))

  const select = section.querySelector<HTMLSelectElement>('select[aria-label="Room"]')

  return {
    found: true,
    panelText: section.innerText,
    rows,
    select: select
      ? {
          measured: measure(select),
          className: select.getAttribute('class'),
          optionCount: select.options.length,
          value: select.value,
        }
      : null,
  }
}

/** The attention animation's computed state on the live page: the rows and the dots it renders. */
function motionInPage() {
  const selector = '[aria-label="Room decision requests"]'

  const read = (el: HTMLElement | null) => {
    if (!el) return null
    const cs = getComputedStyle(el)
    return {
      animationName: cs.animationName,
      animationDuration: cs.animationDuration,
      animationIterationCount: cs.animationIterationCount,
    }
  }

  const section = document.querySelector<HTMLElement>(selector)

  return {
    prefersReducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    renderedPendingRows: section?.querySelectorAll('article.animate-pulse-glow').length ?? 0,
    renderedPingDots: section?.querySelectorAll('span.animate-ping').length ?? 0,
    firstRow: read(section?.querySelector<HTMLElement>('article') ?? null),
  }
}

/**
 * The attention classes' computed animation, on a probe carrying the same class names.
 *
 * The room has no pending row, so the element that would run the attention loop is not on the
 * page; the class a pending row carries is measured instead, against the page's own stylesheets.
 * The probe is created, measured and removed in the page - nothing is sent anywhere.
 */
function attentionProbeInPage() {
  const probe = (className: string) => {
    const el = document.createElement('div')
    el.className = className
    el.style.position = 'fixed'
    el.style.top = '-1000px'
    document.body.appendChild(el)
    const cs = getComputedStyle(el)
    const reading = {
      animationName: cs.animationName,
      animationDuration: cs.animationDuration,
      animationIterationCount: cs.animationIterationCount,
    }
    el.remove()
    return reading
  }

  return {
    prefersReducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    pulseGlow: probe('animate-pulse-glow'),
    ping: probe('animate-ping'),
    pulse: probe('animate-pulse'),
  }
}

/** Which served sheet carries the attention rule and its reduce gate (enumerate the page's sheets). */
function attentionCssInPage() {
  const hits: { sheet: string; media: string | null; selector: string; animation: string }[] = []
  const keyframes: string[] = []

  const walk = (rules: CSSRuleList, media: string | null, sheet: string) => {
    for (const rule of Array.from(rules)) {
      // A style rule is decided by selectorText first: a modern Chrome CSSStyleRule also exposes
      // an (empty) cssRules through CSS nesting, so "has cssRules" alone misclassifies it.
      if ('selectorText' in rule && typeof rule.selectorText === 'string') {
        const styleRule = rule as CSSStyleRule
        if (/animate-(pulse-glow|ping|pulse)\b/.test(styleRule.selectorText)) {
          hits.push({ sheet, media, selector: styleRule.selectorText, animation: styleRule.style.animation })
        }
        continue
      }
      if ('conditionText' in rule && 'cssRules' in rule) {
        const nested = rule as CSSMediaRule
        walk(nested.cssRules, nested.conditionText, sheet)
        continue
      }
      if ('name' in rule) {
        const frames = rule as CSSKeyframesRule
        if (typeof frames.name === 'string') keyframes.push(frames.name)
      }
    }
  }

  for (const sheet of Array.from(document.styleSheets)) {
    const label = sheet.href ?? 'inline'
    try {
      walk(sheet.cssRules, null, label)
    } catch {
      // A cross-origin sheet refuses cssRules; that sheet is not this app's CSS.
      hits.push({ sheet: label, media: null, selector: '(unreadable, cross-origin)', animation: '' })
    }
  }

  return {
    sheetCount: document.styleSheets.length,
    hits,
    keyframes: keyframes.filter((name) => /pulse|ping/i.test(name)),
  }
}

/** Which served script is the select-simple chunk, and which class string it ships. */
async function shippedSelectChunk(page: Page) {
  return page.evaluate(async () => {
    const scripts = performance
      .getEntriesByType('resource')
      .map((entry) => entry.name)
      .filter((url) => /\.js(\?|$)/.test(url))
    const chunks = scripts.filter((url) => /select-simple-[^/]*\.js/.test(url))
    const targets = chunks.length > 0 ? chunks : scripts

    const results = []
    for (const url of targets) {
      const text = await fetch(url).then((response) => response.text())
      results.push({
        url,
        hasHeightFix: text.includes('min-h-[2.5rem]'),
        hasOldH10: /theme-input flex h-10 w-full/.test(text),
        selectClassString: /theme-input[^"']{0,130}/.exec(text)?.[0] ?? null,
      })
    }

    return {
      scriptCount: scripts.length,
      selectChunkUrls: chunks,
      searched: targets.length,
      results: results.filter((row) => row.selectClassString || row.hasHeightFix),
    }
  })
}

function writeEvidence(name: string, payload: unknown): string {
  fs.mkdirSync(OUT, { recursive: true })
  const file = path.join(OUT, `${ROOM}-${name}.json`)
  fs.writeFileSync(file, JSON.stringify(payload, null, 2))
  return file
}

test.describe('Decision Requests panel on production', () => {
  test('lists the room open decisions on the live route, unclipped, with the attention animation', async ({
    page,
  }) => {
    test.setTimeout(240_000)

    const apiCalls: { url: string; status: number | null; method: string }[] = []
    const decisionReads: { url: string; status: number; body: unknown }[] = []

    page.on('response', (response) => {
      const url = response.url()
      if (/\/api\//.test(url)) {
        apiCalls.push({ url, status: response.status(), method: response.request().method() })
      }
      if (/\/api\/v2\/rooms\/[^/]+\/decisions(\?|$)/.test(url)) {
        const entry = { url, status: response.status(), body: null as unknown }
        decisionReads.push(entry)
        void response
          .json()
          .then((body) => {
            entry.body = body
          })
          .catch(() => {})
      }
    })
    page.on('request', (request) => {
      if (/\/api\//.test(request.url()) && request.method() !== 'GET') {
        apiCalls.push({ url: request.url(), status: null, method: request.method() })
      }
    })

    const opened = await openPanelForRoom(page)

    const reading = await page.evaluate(readPanelInPage)
    const motion = await page.evaluate(motionInPage)
    const css = await page.evaluate(attentionCssInPage)
    const probe = await page.evaluate(attentionProbeInPage)
    const shipped = await shippedSelectChunk(page)

    // The dashboard itself POSTs /api/v2/branches/summaries/bulk as a read; the routes that would
    // be writes are the panel's own answer/message calls, and none of them may leave this run.
    const writes = apiCalls.filter(
      (call) => call.method !== 'GET' && /\/(decisions|answer|messages)\b/.test(call.url)
    )
    const openrig = apiCalls.filter((call) => /openrig/.test(call.url))
    const read = decisionReads.filter((entry) => entry.url.includes(`/rooms/${ROOM}/decisions`)).at(-1) ?? null

    const body = read?.body
    const rows =
      body && typeof body === 'object' && 'decisions' in body && Array.isArray(body.decisions)
        ? body.decisions
        : []
    const states = rows.map((row) =>
      row && typeof row === 'object' && 'state' in row && typeof row.state === 'string' ? row.state : 'unknown'
    )
    const labels = reading.rows.map((row) => row.state)

    const evidence = {
      room: ROOM,
      path: PAGE_PATH,
      opened,
      decisionReads,
      reading,
      motion,
      attentionProbe: probe,
      attentionCss: css,
      shippedSelectChunk: shipped,
      apiCalls,
    }
    const evidenceFile = writeEvidence('default-motion', evidence)
    console.log('EVIDENCE ' + evidenceFile)
    console.log(
      'SUMMARY ' +
        JSON.stringify(
          {
            opened,
            decisionReads: decisionReads.map((entry) => ({ url: entry.url, status: entry.status })),
            decisionStates: states,
            renderedLabels: labels,
            select: reading.select,
            motion,
            attentionProbe: probe,
            attentionCss: css,
            shipped: shipped.results,
          },
          null,
          2
        )
    )

    expect(opened.panelVisible, 'the Decision Requests panel renders in the dashboard sidebar').toBe(true)
    expect(openrig, 'no request goes to the retired /api/v2/openrig route').toHaveLength(0)
    expect(writes, 'the panel issued no answer/message write').toHaveLength(0)
    expect(decisionReads.length, 'the panel read a room decisions route').toBeGreaterThan(0)
    expect(read, `the panel read /api/v2/rooms/${ROOM}/decisions`).not.toBeNull()
    expect(read!.status, 'the decision read answers 200').toBe(200)

    if (reading.select) {
      expect(
        reading.select.measured.shortForOwnLineBox,
        'the room Select is not shorter than its own line box + padding'
      ).toBe(false)
    }

    // The fix is in the served bytes, not only in the source line.
    const selectChunks = shipped.results.filter((row) => row.selectClassString)
    expect(selectChunks.length, 'the served build carries a select-simple class string').toBeGreaterThan(0)
    for (const row of selectChunks) {
      expect(row.hasOldH10, `${row.url} does not carry the old h-10 class`).toBe(false)
    }
    expect(
      selectChunks.some((row) => row.hasHeightFix),
      'the served select chunk carries the min-h-[2.5rem] height fix'
    ).toBe(true)

    // That chunk is select-simple, not this panel's picker: the panel renders its own Select, so a
    // regression in the panel's class would leave the check above green. Assert it where its class is
    // visible - on the rendered element - and assert the shape the fix has (a floor that still lets the
    // control grow), not one rem literal: a legitimate 2.25rem <-> 2.5rem change must not go red.
    const panelSelectClass = reading.select?.className ?? ''
    expect(
      panelSelectClass,
      'the panel Select puts a min-h-[...] floor on its height'
    ).toMatch(/min-h-\[[\d.]+(rem|px|em)\]/)
    expect(panelSelectClass, 'the panel Select carries no fixed height class').not.toMatch(/\bh-(8|9|10|11|12)\b/)

    // The attention loop the pending row's class carries is wired in the served CSS and would run.
    expect(probe.pulseGlow.animationName, 'animate-pulse-glow starts the pulseGlow loop').toBe('pulseGlow')
    expect(probe.pulseGlow.animationDuration).toBe('2.5s')
    expect(probe.pulseGlow.animationIterationCount).toBe('infinite')
    expect(probe.ping.animationName, 'animate-ping starts Tailwind ping').toBe('ping')
    expect(probe.pulse.animationName, 'animate-pulse starts Tailwind pulse').toBe('pulse')
    expect(css.keyframes, 'the served CSS defines the pulseGlow keyframes').toContain('pulseGlow')

    if (motion.renderedPendingRows === 0) {
      console.log(
        `NOT OBSERVABLE on a live row: the room has no pending decision (${labels.length} rows rendered, all "${labels[0]}"), so the attention row and its two dots are not on the page - the class measurement above is a probe, not that row`
      )
    }

    // ROW MEASUREMENTS, LAST AND GUARDED. Everything above measures the panel, the served build and
    // the served CSS without depending on how many decisions the room holds. These three read the
    // rows themselves, and an empty room is the absence of a subject rather than a product failure:
    // the shape checks above stay red-able (the 200, the read's own route, the panel's presence) and
    // only these are skipped, with the reason on the report.
    test.skip(reading.rows.length === 0, 'no open decision to measure: the room rendered no row')

    // The open list is pending + answered and nothing else: a resolved row stays out of it.
    const openLabels = ['waiting for you', 'awaiting the room']
    for (const label of labels) {
      expect(openLabels, `${label} is a pending/answered row label`).toContain(label)
    }
    expect(states.length, 'the API returned the room decision rows').toBeGreaterThan(0)

    // No panel element hides its own overflow: the shape clipping takes.
    const clipped = reading.rows.flatMap((row) =>
      row.elements.filter((el) => el.clipped).map((el) => `${el.state}: ${el.tag} ${el.text}`)
    )
    expect(clipped, 'no panel element clips its own content box').toHaveLength(0)
  })

  test('the room rows are not vertically clipped', async ({ page }) => {
    test.setTimeout(240_000)
    await openPanelForRoom(page)

    const reading = await page.evaluate(readPanelInPage)

    // SHAPE FIRST, and RED-able: the panel is there and its read carries a rows ARRAY. Neither check
    // depends on how many decisions the room holds.
    expect(reading.found, 'the panel section was found').toBe(true)
    expect(Array.isArray(reading.rows), 'the panel read a rows array').toBe(true)

    // An empty room is the absence of a subject, not a product failure: only the row measurement is
    // skipped, and the reason rides the report.
    test.skip(reading.rows.length === 0, 'no open decision to measure: the room rendered no row')

    const evidenceFile = writeEvidence('clipping', reading)
    console.log('EVIDENCE ' + evidenceFile)
    console.log(
      'CLIPPING ' +
        JSON.stringify(
          {
            found: reading.found,
            panelText: reading.panelText,
            select: reading.select,
            rows: reading.rows.map((row) => ({
              state: row.state,
              summary: row.summary,
              elements: row.elements.length,
              clipped: row.elements.filter((el) => el.clipped).length,
              spilling: row.elements.filter((el) => el.spilling).length,
            })),
          },
          null,
          2
        )
    )

    const clipped = reading.rows.flatMap((row) =>
      row.elements.filter((el) => el.clipped).map((el) => `${row.state}: ${el.tag} ${el.text}`)
    )
    expect(clipped, 'no row element clips its own content box').toHaveLength(0)
  })

  /**
   * A failed read names its own status. The failure is INJECTED in the browser - the intercepted
   * request never reaches production and nothing on the server is touched - because a healthy route
   * cannot be made to fail on demand. It proves the client's failure rendering for a status the route
   * returns; it does NOT prove that production's route ever fails.
   *
   * The status TOKEN is asserted, not one phrase: the criterion is "shows a failed read with its
   * status", so a reworded message that still names 503 passes, while a message that hides the status
   * fails. The panel's failed-read branch itself must still say it could not read.
   */
  test('a failed decisions read names its status', async ({ page }) => {
    test.setTimeout(180_000)

    // Registered before the panel mounts: the read must fail on its first call.
    await page.route('**/api/v2/rooms/**/decisions', (route) =>
      route.request().method() === 'GET'
        ? route.fulfill({ status: 503, contentType: 'text/plain', body: 'gateway down' })
        : route.continue()
    )

    await signIn(page)
    await page.goto(PAGE_PATH)

    const panel = page.getByRole('region', { name: 'Room decision requests' })
    await expect(panel).toBeVisible({ timeout: 45_000 })
    // The hook settles into its failure branch only after the rejected read, so assert on that branch
    // rather than sampling the panel's loading text a fixed moment later.
    await expect(panel, 'the panel rendered its failed-read branch').toContainText('Could not read', {
      timeout: 30_000,
    })
    // The status is asserted with Playwright's own retrying matcher, not a one-shot innerText() sample:
    // branch and status must both hold of the rendered region, and a sample taken once cannot tell a
    // settled render from one still settling. The matcher reads textContent, where the status runs
    // straight into the next element's label ("HTTP 503Send request to lead"), so the token's boundary
    // is a non-digit, not \b: /\b503\b/ fails there while the panel renders the status correctly.
    // Digit bounds keep the token honest (a 599 reds) without pinning the words around it.
    await expect(panel, 'the failed read names its status').toContainText(/(?<!\d)503(?!\d)/, {
      timeout: 30_000,
    })
    // Hyphen, not a space: evidence.go reads a line matching /^FAILED\s+(\S+)/ as a pytest failure and
    // would store "READ" as the failed test name for a run whose tests all passed.
    console.log(
      'FAILED-READ ' + JSON.stringify({ status: 503, text: (await panel.innerText()).replace(/\s+/g, ' ') })
    )
  })
})

test.describe('Decision Requests panel under prefers-reduced-motion: reduce', () => {
  test('switches the attention animation off', async ({ browser }) => {
    test.setTimeout(240_000)

    // An explicit context: the reduce preference must be a measured fact of THIS page, not a
    // property the spec assumes it passed down.
    const context = await browser.newContext({ reducedMotion: 'reduce' })
    const page = await context.newPage()
    try {
      const opened = await openPanelForRoom(page)

      const motion = await page.evaluate(motionInPage)
      const probe = await page.evaluate(attentionProbeInPage)
      const css = await page.evaluate(attentionCssInPage)
      const evidence = { room: ROOM, path: PAGE_PATH, opened, motion, attentionProbe: probe, attentionCss: css }
      const evidenceFile = writeEvidence('reduced-motion', evidence)
      console.log('EVIDENCE ' + evidenceFile)
      console.log('REDUCED ' + JSON.stringify({ motion, attentionProbe: probe }, null, 2))

      expect(motion.prefersReducedMotion, 'the page really reports prefers-reduced-motion: reduce').toBe(true)
      expect(opened.panelVisible, 'the panel renders under reduce too').toBe(true)

      // The reduce block wins over the utilities: all three attention classes compute to none.
      for (const [label, reading] of Object.entries(probe)) {
        if (typeof reading === 'string' || typeof reading === 'boolean') continue
        expect(reading.animationName, `${label} is switched off under reduce`).toBe('none')
      }
      const reduceRules = css.hits.filter((hit) => hit.media?.includes('prefers-reduced-motion'))
      expect(reduceRules.length, 'the served CSS carries a prefers-reduced-motion rule for the attention classes').toBeGreaterThan(0)

      if (motion.renderedPendingRows === 0) {
        console.log(
          'NOT OBSERVABLE on a live row: the room has no pending decision, so the reduce request was measured on the class (probe), not on a rendered attention row'
        )
      }
    } finally {
      await context.close()
    }
  })
})

/**
 * THE PENDING ROW, MANUFACTURED IN THE BROWSER.
 *
 * The attention state has no live subject: the panel's own Room picker offers one room and every row
 * that room holds is answered (measured 2026-10-16), so no production read can render a pending row.
 * These two tests FULFIL the panel's own decisions GET inside the browser with one pending decision -
 * the request never reaches production - and intercept the answer endpoint to ABORT it, asserting that
 * no answer call was attempted, so a click cannot write even by accident.
 *
 * WHAT THIS PROVES AND WHAT IT DOES NOT, named: it proves the panel RENDERS a pending decision and what
 * that row's attention state computes to, which is the half no room could show; it does NOT prove that
 * production's data carries a pending decision - that is a property of the tenant's queue, not of the
 * panel.
 */

/** The one pending decision the injected read answers with. Its summary names the injection. */
const INJECTED_ROW_TOKEN = 'PROBE (injected in the browser, no production row exists)'

const pendingPayload = {
  decisions: [
    {
      id: 'e2e-pending-0001',
      qitem_id: 'qitem-e2e-pending-0001',
      author_seat_key: 'lead',
      summary: `${INJECTED_ROW_TOKEN}: a pending ask whose summary is long enough to wrap in the sidebar`,
      detail:
        'Injected by the spec so the pending state has a rendered subject. Nothing was written, and the read never reached production.',
      questions: [
        {
          id: 'q1',
          question: 'Probe question: which way?',
          options: [
            { id: 'o1', label: 'The first option' },
            { id: 'o2', label: 'The second option', recommended: true },
          ],
        },
      ],
      answers: {},
      state: 'pending',
      created_at: '2026-10-16T17:00:00Z',
      answered_at: null,
    },
  ],
}

/**
 * Answer the panel's decisions GET in the browser and refuse the answer write.
 *
 * The answer route is both counted and ABORTED: `answerCalls` must stay empty, and an accidental click
 * must be unable to reach production.
 */
async function injectPendingDecision(page: Page, answerCalls: string[]): Promise<void> {
  await page.route('**/api/v2/rooms/**/decisions', (route) =>
    route.request().method() === 'GET'
      ? route.fulfill({
          status: 200,
          headers: {
            'content-type': 'application/json',
            'access-control-allow-origin': '*',
            'access-control-allow-headers': '*',
          },
          body: JSON.stringify(pendingPayload),
        })
      : route.continue()
  )
  await page.route('**/api/v2/rooms/**/decisions/**', (route) => {
    const request = route.request()
    if (request.method() === 'GET') return route.continue()
    answerCalls.push(`${request.method()} ${request.url()}`)
    return route.abort()
  })
}

/** Open the dashboard and wait for the injected pending row to render. */
async function openInjectedPendingRow(page: Page): Promise<void> {
  // The route above is registered before this call, so the panel's first read is the fulfilled one.
  const opened = await openPanelForRoom(page)
  expect(opened.panelVisible, 'the panel renders').toBe(true)

  const panel = page.getByRole('region', { name: 'Room decision requests' })
  // The row renders as soon as the fulfilled read resolves, so assert on the row itself rather than
  // sampling the panel at a fixed moment.
  await expect(panel, 'the injected pending row rendered').toContainText(INJECTED_ROW_TOKEN, {
    timeout: 30_000,
  })
  await expect(panel, 'the injected row carries the pending label').toContainText('waiting for you', {
    timeout: 30_000,
  })
}

/** The pending row's rendered attention state, read out of the page. */
function readPendingRowInPage() {
  const section = document.querySelector<HTMLElement>('[aria-label="Room decision requests"]')
  const articles = section ? Array.from(section.querySelectorAll<HTMLElement>('article')) : []
  const row = articles.find((a) => (a.textContent ?? '').includes('PROBE')) ?? articles[0] ?? null

  const motion = (el: Element | null) => {
    if (!el) return null
    const cs = getComputedStyle(el)
    return {
      className: el.getAttribute('class'),
      animationName: cs.animationName,
      animationDuration: cs.animationDuration,
      animationIterationCount: cs.animationIterationCount,
    }
  }

  const measure = (el: HTMLElement) => {
    const cs = getComputedStyle(el)
    const lineHeight = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.2
    const needed = Math.round(lineHeight + parseFloat(cs.paddingTop) + parseFloat(cs.paddingBottom) + 2)
    const overflows = el.scrollHeight > el.clientHeight + 1
    return {
      tag: el.tagName.toLowerCase(),
      text: (el.textContent ?? '').trim().replace(/\s+/g, ' ').slice(0, 60),
      clientHeight: el.clientHeight,
      scrollHeight: el.scrollHeight,
      overflowY: cs.overflowY,
      neededHeight: needed,
      clipped: overflows && cs.overflowY !== 'visible',
      spilling: overflows && cs.overflowY === 'visible',
      shortForOwnLineBox: el.clientHeight + 1 < needed,
    }
  }

  const chip = row?.querySelector<HTMLElement>('span.uppercase') ?? null
  const chipStyle = chip ? getComputedStyle(chip) : null
  const rowStyle = row ? getComputedStyle(row) : null
  const badgeText = section
    ? Array.from(section.querySelectorAll<HTMLElement>('span'))
        .map((span) => (span.textContent ?? '').trim())
        .filter((text) => /^\d+$/.test(text))
    : []

  return {
    found: Boolean(section),
    prefersReducedMotion: window.matchMedia('(prefers-reduced-motion: reduce)').matches,
    articleCount: articles.length,
    rowFound: Boolean(row),
    rowText: (row?.innerText ?? '').replace(/\s+/g, ' ').slice(0, 240),
    stateLabel: chip?.textContent?.trim() ?? null,
    pendingClassOnRow: Boolean(row?.className.includes('animate-pulse-glow')),
    rowMotion: motion(row),
    rowPulseDot: motion(row?.querySelector('span.animate-pulse') ?? null),
    pingDots: section ? section.querySelectorAll('span.animate-ping').length : 0,
    pingDotMotion: motion(section?.querySelector('span.animate-ping') ?? null),
    badgeText,
    /**
     * The accent token as theme.css declares it (hex) plus the row's own painted
     * colours. The colours are asserted, not just recorded: F1 was that the accent
     * border and tint emitted no rule at all, so a row that paints the default
     * grey is the defect (task 470c7439). The spec parses both spellings - see
     * `e2e/colour.ts`.
     */
    accentToken: getComputedStyle(document.documentElement).getPropertyValue('--color-accent').trim(),
    rowBorderTopColor: rowStyle?.borderTopColor ?? null,
    rowBackgroundColor: rowStyle?.backgroundColor ?? null,
    chipColor: chipStyle?.color ?? null,
    chipBackground: chipStyle?.backgroundColor ?? null,
    rowElements: row ? [row, ...Array.from(row.querySelectorAll<HTMLElement>('*'))].map(measure) : [],
  }
}

test.describe('Decision Requests panel: the pending row, rendered by an injected read', () => {
  test('renders the pending row with its attention animation running', async ({ page }) => {
    test.setTimeout(240_000)

    const answerCalls: string[] = []
    await injectPendingDecision(page, answerCalls)
    await openInjectedPendingRow(page)

    const reading = await page.evaluate(readPendingRowInPage)
    const evidenceFile = writeEvidence('pending-row', reading)
    console.log('EVIDENCE ' + evidenceFile)
    console.log(
      'PENDING-ROW ' +
        JSON.stringify({ ...reading, rowElements: reading.rowElements.length }, null, 2)
    )

    expect(reading.found, 'the panel section was found').toBe(true)
    expect(reading.articleCount, 'exactly the injected row is listed').toBe(1)
    expect(reading.pendingClassOnRow, 'the pending row carries the attention class').toBe(true)
    expect(reading.rowMotion?.animationName, 'the row runs the pulseGlow loop').toBe('pulseGlow')
    expect(reading.rowMotion?.animationDuration, 'the row loops at 2.5s').toBe('2.5s')
    expect(reading.rowMotion?.animationIterationCount, 'the loop does not stop').toBe('infinite')
    expect(reading.pingDots, 'the header ping dot is rendered').toBeGreaterThan(0)
    expect(reading.rowPulseDot?.animationName, 'the row dot pulses').toBe('pulse')
    expect(reading.badgeText, 'the pending count badge is rendered').toEqual(['1'])
    expect(reading.stateLabel, 'the state chip names the pending state').toBe('waiting for you')

    // F1's end-to-end acceptance. Before the registration fix these two colours were
    // Tailwind's default grey with no alpha at all, because `border-accent/40` and
    // `bg-accent/[0.03]` compiled to no rule; the parse accepts `rgb()` and
    // `color(srgb ... / a)`, so a failure here means a dead class, not a spelling.
    const accent = parseHexColour(reading.accentToken)
    expect(accent, `the accent token is a hex colour; read ${reading.accentToken}`).not.toBeNull()

    const border = parsePaintedColour(reading.rowBorderTopColor ?? '')
    expect(border, `the pending row's border parses; read ${reading.rowBorderTopColor}`).not.toBeNull()
    expect(border!.a, `border-accent/40 paints at 0.4; read ${reading.rowBorderTopColor}`).toBeCloseTo(0.4, 2)
    expect(
      sameHue(border!, accent!),
      `the border is the accent ${formatChannels(accent!)}; read ${formatChannels(border!)}`
    ).toBe(true)

    const tint = parsePaintedColour(reading.rowBackgroundColor ?? '')
    expect(tint, `the pending row's tint parses; read ${reading.rowBackgroundColor}`).not.toBeNull()
    expect(tint!.a, `bg-accent/[0.03] paints at 0.03; read ${reading.rowBackgroundColor}`).toBeCloseTo(0.03, 3)
    expect(
      sameHue(tint!, accent!),
      `the tint is the accent ${formatChannels(accent!)}; read ${formatChannels(tint!)}`
    ).toBe(true)

    const chipTint = parsePaintedColour(reading.chipBackground ?? '')
    expect(chipTint, `the state chip's tint parses; read ${reading.chipBackground}`).not.toBeNull()
    expect(chipTint!.a, `bg-accent/15 paints at 0.15; read ${reading.chipBackground}`).toBeCloseTo(0.15, 2)

    const clipped = reading.rowElements.filter((el) => el.clipped).map((el) => `${el.tag} ${el.text}`)
    expect(clipped, 'no element of the pending row clips its own content box').toHaveLength(0)

    expect(answerCalls, 'no answer write was attempted').toHaveLength(0)
  })

  test('switches the animation off under prefers-reduced-motion', async ({ browser }) => {
    test.setTimeout(240_000)

    // An explicit context, as the live reduce test uses: the preference must be a measured fact of
    // THIS page rather than a property the spec assumes it passed down.
    const context = await browser.newContext({ reducedMotion: 'reduce' })
    const page = await context.newPage()
    try {
      const answerCalls: string[] = []
      await injectPendingDecision(page, answerCalls)
      await openInjectedPendingRow(page)

      const reading = await page.evaluate(readPendingRowInPage)
      const probe = await page.evaluate(attentionProbeInPage)
      const evidenceFile = writeEvidence('pending-row-reduced-motion', { reading, attentionProbe: probe })
      console.log('EVIDENCE ' + evidenceFile)
      console.log('PENDING-ROW-REDUCE ' + JSON.stringify({ ...reading, rowElements: reading.rowElements.length }, null, 2))
      // The still cue, recorded: with every animation off, what still marks the row
      // (the chip, the dots, the badge). The accent border and tint are part of it now
      // that they paint (F1 landed), which is why they are asserted below rather than
      // logged as absent.
      console.log(
        'PENDING-ROW-STILL-CUE ' +
          JSON.stringify({
            stateLabel: reading.stateLabel,
            badge: reading.badgeText,
            chipColor: reading.chipColor,
            chipBackground: reading.chipBackground,
            rowBorderTopColor: reading.rowBorderTopColor,
            rowBackgroundColor: reading.rowBackgroundColor,
          })
      )

      expect(reading.found, 'the panel section was found').toBe(true)
      expect(reading.prefersReducedMotion, 'the page really reports prefers-reduced-motion: reduce').toBe(true)
      expect(reading.articleCount, 'exactly the injected row is listed').toBe(1)
      expect(reading.rowMotion?.animationName, 'the row animation is off').toBe('none')
      expect(reading.rowPulseDot?.animationName, 'the row dot is off').toBe('none')
      expect(reading.pingDotMotion?.animationName, 'the ping dot is off').toBe('none')
      for (const [label, probeReading] of Object.entries(probe)) {
        if (typeof probeReading === 'string' || typeof probeReading === 'boolean') continue
        expect(probeReading.animationName, `${label} is switched off under reduce`).toBe('none')
      }

      // The border is paint, not motion: it must survive reduce, and it is the cue that
      // does not depend on an animation the reader may have switched off.
      const borderUnderReduce = parsePaintedColour(reading.rowBorderTopColor ?? '')
      expect(borderUnderReduce, `the row border parses; read ${reading.rowBorderTopColor}`).not.toBeNull()
      expect(
        borderUnderReduce!.a,
        `border-accent/40 still paints at 0.4 under reduce; read ${reading.rowBorderTopColor}`
      ).toBeCloseTo(0.4, 2)

      expect(answerCalls, 'no answer write was attempted').toHaveLength(0)
    } finally {
      await context.close()
    }
  })
})
