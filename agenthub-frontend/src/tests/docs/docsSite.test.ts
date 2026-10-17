import { describe, it, expect } from 'vitest';
import { buildSections, docSections, resolveDocHref, stripOrder } from '../../docs/docsSite';

const ROOT = '../../../ai_docs/public-docs/';

describe('stripOrder', () => {
  it('drops the ordering number and the extension, never the name', () => {
    expect(stripOrder('02-five-minute-team.md')).toBe('five-minute-team');
    expect(stripOrder('01-quickstart')).toBe('quickstart');
    expect(stripOrder('troubleshooting-catalog.md')).toBe('troubleshooting-catalog');
  });
});

describe('buildSections', () => {
  it('orders sections and pages by their numbers and titles a page by its first heading', () => {
    const sections = buildSections(
      {
        [`${ROOT}02-architecture/01-how-it-works.md`]: '# How It Works\n\nbody',
        [`${ROOT}01-quickstart/02-team.md`]: 'no heading',
        [`${ROOT}01-quickstart/01-prerequisites.md`]: '# Prerequisites\n',
      },
      ROOT,
    );
    expect(sections.map((section) => section.title)).toEqual(['Quickstart', 'Architecture']);
    expect(sections[0].pages.map((page) => [page.id, page.title])).toEqual([
      ['quickstart/prerequisites', 'Prerequisites'],
      ['quickstart/team', 'Team'],
    ]);
  });

  it('reads the real ai_docs/public-docs tree', () => {
    // The glob is relative to the module: an empty site means the tree moved or the
    // Dockerfile stopped copying it, which would publish a docs page with nothing in it.
    expect(docSections.length).toBeGreaterThan(0);
    expect(docSections[0].pages[0].id).toBe('quickstart/overview');
  });
});

describe('resolveDocHref', () => {
  const assets = { [`${ROOT}01-quickstart/architecture.png`]: '/assets/architecture-abc123.png' };

  it('turns a relative page link into a /docs route, ignoring the numbers', () => {
    expect(resolveDocHref('quickstart/overview', '01-prerequisites.md', assets)).toBe('/docs/quickstart/prerequisites');
    expect(resolveDocHref('quickstart/daily-operations', '../03-production-performance/05-jev-decisions.md', assets)).toBe(
      '/docs/production-performance/jev-decisions',
    );
    expect(resolveDocHref('quickstart/overview', './02-team.md#launch', assets)).toBe('/docs/quickstart/team#launch');
  });

  it('turns a relative image into the built asset URL', () => {
    expect(resolveDocHref('quickstart/overview', 'architecture.png', assets)).toBe('/assets/architecture-abc123.png');
  });

  it('leaves absolute, external, anchor and unresolvable paths as written', () => {
    for (const href of ['/sessions', 'https://example.com/a.md', '#section', 'mailto:a@b.c', '../../outside.md', 'missing.png']) {
      expect(resolveDocHref('quickstart/overview', href, assets)).toBe(href);
    }
  });
});
