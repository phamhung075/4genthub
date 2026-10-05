import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from './../test-utils';
import { ApiDocsPage, applyTokens, slugifyHeading } from '../../pages/ApiDocsPage';
import { toSanitizedHtml } from '../../lib/markdownHtml';
import { API_BASE_URL } from '../../config/environment';

// The document is imported raw by the page. The real file is asserted through
// the page; the mock below proves the table of contents FOLLOWS the content
// rather than a hand-maintained list, and it is the only place a heading is
// added and removed without touching the real document.
vi.mock('../../docs/api-reference.en.md?raw', () => ({
  default: [
    '# Mocked title',
    '',
    '## First section',
    '',
    'Body text with a token: {{API_ORIGIN}}',
    '',
    '### Nested section',
    '',
    '## First section',
    '',
    'A duplicate heading, which must get a suffixed id.',
  ].join('\n'),
}));

describe('applyTokens', () => {
  it('fills a known token and leaves an unknown one untouched', () => {
    const out = applyTokens('origin={{API_ORIGIN}} other={{NOT_A_TOKEN}}', {
      API_ORIGIN: 'https://api.example.test',
    });
    expect(out).toBe('origin=https://api.example.test other={{NOT_A_TOKEN}}');
  });

  it('keeps the token visible when the value is missing, rather than blanking it', () => {
    // An empty string looks like a styling bug; a visible token is a finding.
    expect(applyTokens('mcp={{MCP_URL}}', { MCP_URL: undefined })).toBe('mcp={{MCP_URL}}');
    expect(applyTokens('mcp={{MCP_URL}}', { MCP_URL: '' })).toBe('mcp={{MCP_URL}}');
    expect(applyTokens('v={{ VERSION }}', { VERSION: '0.0.17' })).toBe('v=0.0.17');
  });
});

describe('slugifyHeading', () => {
  it('produces an ascii anchor and falls back rather than returning empty', () => {
    expect(slugifyHeading('Base URL')).toBe('base-url');
    expect(slugifyHeading('Data & results!')).toBe('data-results');
    expect(slugifyHeading('---')).toBe('section');
  });
});

describe('toSanitizedHtml (the one sanitizer policy)', () => {
  it('renders GFM and drops the interactive elements the policy forbids', () => {
    const html = toSanitizedHtml(
      ['| a | b |', '| - | - |', '| 1 | 2 |', '', '<form><input value="x"></form>', '<script>alert(1)</script>'].join('\n'),
    );
    expect(html).toContain('<table>'); // GFM survives
    expect(html).not.toContain('<form');
    expect(html).not.toContain('<input');
    expect(html).not.toContain('<script');
  });
});

describe('ApiDocsPage', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('builds the table of contents from the rendered headings, in order, with working ids', async () => {
    render(<ApiDocsPage />);

    const toc = await screen.findByTestId('api-docs-toc');
    const entries = Array.from(toc.querySelectorAll('a'));
    const body = screen.getByTestId('api-docs-body');
    const headings = Array.from(body.querySelectorAll('h2, h3'));

    // The anti-drift invariant: the list IS the rendered headings, no more and
    // no fewer, so a heading added to the markdown appears with no other edit.
    expect(entries.map((a) => a.textContent)).toEqual(headings.map((h) => h.textContent));
    expect(entries).toHaveLength(3);

    // Every entry links to an element that exists, and duplicate heading text
    // gets a suffixed id rather than colliding.
    for (const [index, entry] of entries.entries()) {
      const id = entry.getAttribute('href');
      expect(id).toBe(`#${headings[index].id}`);
      expect(body.querySelector(id as string)).not.toBeNull();
    }
    const ids = headings.map((h) => h.id);
    expect(new Set(ids).size).toBe(ids.length);
    expect(ids).toContain('first-section-1');
  });

  it('shows the live origin and the health version, and the token when health is unreachable', async () => {
    (global.fetch as any).mockResolvedValue({ ok: true, json: async () => ({ version: '0.0.17' }) });

    render(<ApiDocsPage />);

    await waitFor(() => {
      expect(screen.getByTestId('api-docs-version')).toHaveTextContent('0.0.17');
    });
    expect(screen.getByTestId('api-docs-origin')).toHaveTextContent(API_BASE_URL);

    // The property that matters is SUBSTITUTION, not that a configured string is
    // printed: the document's tokens are gone and the deployment's own values
    // took their place.
    const body = screen.getByTestId('api-docs-body').textContent ?? '';
    expect(body).toContain(API_BASE_URL);
    expect(body).not.toContain('{{API_ORIGIN}}');
  });

  it('leaves the version token visible when /health fails', async () => {
    (global.fetch as any).mockRejectedValue(new Error('backend down'));

    render(<ApiDocsPage />);

    await waitFor(() => {
      expect(screen.getByTestId('api-docs-version')).toHaveTextContent('{{VERSION}}');
    });
  });
});
