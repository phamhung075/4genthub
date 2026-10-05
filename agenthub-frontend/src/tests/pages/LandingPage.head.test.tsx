import { describe, it, expect, beforeEach } from 'vitest';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { render, screen } from './../test-utils';
import { ThemeProvider } from '../../contexts/ThemeContext';
import { LandingPage, PAGE_TITLE, PAGE_DESCRIPTION } from '../../pages/LandingPage';

// Directive G's acceptance, pinned so it cannot drift:
//  - the static head describes the same product as the page body;
//  - no number appears without a measurement behind it;
//  - the removed fabricated values stay removed.
//
// index.html cannot import the page's constants, so this test reads the file and
// compares, which is the point: hand-maintained copies of one sentence are what
// the criterion exists to catch.
const indexHtml = readFileSync(resolve(process.cwd(), 'index.html'), 'utf8');

describe('the static head and the page agree', () => {
  it('carries the same title and description as the page sets at runtime', () => {
    const title = indexHtml.match(/<title>([^<]*)<\/title>/)?.[1];
    const description = indexHtml.match(/<meta\s+name="description"\s+content="([^"]*)"/s)?.[1];

    expect(title).toBe(PAGE_TITLE);
    expect(description).toBe(PAGE_DESCRIPTION);
  });

  it('carries the og and twitter tags a link preview needs', () => {
    for (const tag of ['og:title', 'og:description', 'og:image', 'og:type', 'og:site_name', 'twitter:card', 'twitter:title', 'twitter:image']) {
      expect(indexHtml).toContain(tag);
    }
  });

  it('names no deployment in the static head', () => {
    // Any hardcoded host would make every self-hosted install advertise someone
    // else's domain; the runtime derives og:url, the canonical link and the
    // absolute image URLs from window.location.origin instead.
    expect(indexHtml).not.toMatch(/4genthub\.com/);
  });

  it('keeps the web-app manifest saying the same thing as the head', () => {
    // The manifest is a third head artifact (install prompt name and description)
    // and it carried the retired "32 specialized AI agents" line.
    const manifest = JSON.parse(readFileSync(resolve(process.cwd(), 'public/manifest.json'), 'utf8'));
    expect(manifest.description).toBe(PAGE_DESCRIPTION);
    expect(manifest.name).toContain('rooms, seats and modules');
    expect(manifest.description).not.toContain('32 specialized');
  });

  it('lists only routes that exist in the app', () => {
    const sitemap = readFileSync(resolve(process.cwd(), 'public/sitemap.xml'), 'utf8');
    const appSource = readFileSync(resolve(process.cwd(), 'src/App.tsx'), 'utf8');
    const locs = [...sitemap.matchAll(/<loc>([^<]*)<\/loc>/g)].map((m) =>
      // Strip the host: what matters here is the path the app must serve.
      m[1].replace(/^https?:\/\/[^/]+/, ''),
    );

    expect(locs.length).toBeGreaterThan(0);
    for (const loc of locs) {
      const path = loc === '/' ? '"/"' : `"${loc}"`;
      expect(appSource).toContain(`path=${path}`);
    }
    // The route that produced this check stays out of the ENTRIES. The comment
    // above the urlset names it deliberately, as the reason the file changed.
    expect(locs).not.toContain('/agents/marketplace');
  });
});

describe('the page body claims only what ships', () => {
  beforeEach(() => {
    // The page reads the theme, and the shared test providers do not include the
    // theme context, so it is supplied here rather than mocked - the body copy is
    // what this test is about.
    render(
      <ThemeProvider>
        <LandingPage />
      </ThemeProvider>,
    );
  });

  it('does not carry the fabricated numbers or the retired claims', () => {
    const text = document.body.textContent ?? '';
    for (const removed of [
      '10x', // no measurement
      '2 minutes', // no measurement
      '99.9%', // no SLA exists
      'Free Forever', // a promise with nothing behind it
      '4-Tier', // the retired Python hierarchy
      'Global → Project → Branch → Task',
      'Task Manager', // the old product name
    ]) {
      expect(text).not.toContain(removed);
    }
  });

  it('one number survives because it is checkable, and the card agrees with it', () => {
    const text = document.body.textContent ?? '';
    // runtime.go:16-19 is the one runtime list: claude-code, codex, agy, omp.
    expect(text).toContain('Claude Code, codex, agy or omp');
    expect(text).toContain('Occupant Runtimes');
  });

  it('publishes structured data with no invented rating, version or screenshot', () => {
    const jsonLd = JSON.parse(document.querySelector('script[type="application/ld+json"]')?.textContent ?? '{}');
    expect(jsonLd.aggregateRating).toBeUndefined();
    expect(jsonLd.softwareVersion).toBeUndefined();
    expect(jsonLd.screenshot).toBeUndefined();
    expect(jsonLd.featureList).toContain('Runtimes: Claude Code, codex, agy, omp');
  });
});
