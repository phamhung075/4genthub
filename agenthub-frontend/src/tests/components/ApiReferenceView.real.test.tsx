/**
 * ApiReferenceView against the REAL generated artefact (DOCS-PAGE.md step 1).
 *
 * THE FIXTURE CASE PROVES THE COMPONENT; THIS PROVES THE INTEGRATION. It imports the module
 * go-dev2's generator wrote - the same build-time import the page will use - so a regeneration
 * that drops a key, empties a list or changes a field reaches THIS suite rather than the page.
 *
 * THE ASSERTIONS ARE DATA-DRIVEN ON PURPOSE: expected counts come from the artefact itself, so
 * a route or tool added by a later regeneration is not a failure here. What these cases catch is
 * the component disagreeing with the artefact - an entry dropped, a field rendered that is not
 * there, or a legitimate empty rendered as an error.
 *
 * The artefact's own empties are expected tonight and are asserted as ABSENT, not as errors:
 * every tool carries `actions: []` until the deferred enum slice lands, and a route whose mount
 * is an inline closure carries `handler: ''`.
 */

import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { ApiReferenceView } from '../../components/docs/ApiReferenceView';
import { apiReference } from '../../docs/apiReference';

const renderReal = () => render(<ApiReferenceView reference={apiReference} />);
const routesRegion = () => screen.getByRole('region', { name: 'HTTP routes' });
const toolsRegion = () => screen.getByRole('region', { name: 'MCP tools' });

describe('ApiReferenceView <-> the generated artefact', () => {
  it('carries the artefact the generator wrote, and it is not empty', () => {
    // A generator that emitted nothing would render "0 routes" and pass every count check.
    expect(apiReference.routes.length).toBeGreaterThan(0);
    expect(apiReference.tools.length).toBeGreaterThan(0);
  });

  it('renders every route and every tool the artefact carries, and the counts agree with it', () => {
    renderReal();

    const routes = within(routesRegion());
    expect(routes.getByText(`${apiReference.routes.length} routes, generated from the mounts rather than typed by hand.`)).toBeInTheDocument();
    expect(routes.getAllByRole('listitem')).toHaveLength(apiReference.routes.length);
    // Unique paths only: two methods on one path are one string in the DOM twice, and that is
    // correct rather than ambiguous - the row COUNT above is what proves nothing was dropped.
    for (const path of new Set(apiReference.routes.map((route) => route.path))) {
      expect(routes.getAllByText(path).length).toBeGreaterThan(0);
    }

    const tools = within(toolsRegion());
    expect(tools.getByText(`${apiReference.tools.length} tools, with the parameters the server advertises.`)).toBeInTheDocument();
    expect(tools.getAllByRole('article')).toHaveLength(apiReference.tools.length);
    for (const tool of apiReference.tools) {
      expect(tools.getByRole('article', { name: tool.name })).toBeInTheDocument();
    }
  });

  it('renders an inline closure as absent wherever the artefact says the handler is empty', () => {
    renderReal();

    // Row by INDEX rather than by path: the component maps the artefact in order, so the nth row
    // is the nth entry, which is exact even when two routes share a path.
    const rows = within(routesRegion()).getAllByRole('listitem');
    const indexOfEmptyHandler = apiReference.routes.findIndex((route) => route.handler === '');
    expect(indexOfEmptyHandler, 'the artefact carries at least one inline closure tonight').toBeGreaterThanOrEqual(0);

    const inline = apiReference.routes[indexOfEmptyHandler];
    const inlineRow = rows[indexOfEmptyHandler];
    expect(inlineRow.textContent?.replace(/\s+/g, '')).toBe(
      `${inline.method}${inline.path}`.replace(/\s+/g, '')
    );

    const indexOfNamed = apiReference.routes.findIndex((route) => route.handler !== '');
    if (indexOfNamed >= 0) {
      expect(rows[indexOfNamed].textContent).toContain(apiReference.routes[indexOfNamed].handler);
    }
  });

  it('renders the action badges for exactly the tools whose artefact entry declares them', () => {
    renderReal();

    const withActions = apiReference.tools.filter((tool) => tool.actions.length > 0);
    // Tonight that set is empty - the enum slice is deferred - and an empty set must render no
    // label anywhere rather than ten claims that a tool has no actions.
    expect(screen.queryAllByText('Actions')).toHaveLength(withActions.length);
  });

  it("renders the real schema verbatim for every tool that carries parameters", () => {
    renderReal();

    for (const tool of apiReference.tools) {
      const article = within(toolsRegion()).getByRole('article', { name: tool.name });
      const block = article.querySelector('pre') as HTMLElement;
      expect(JSON.parse(block.textContent ?? '')).toEqual(tool.parameters);
    }
  });

  it('carries no loading and no failure state against the real artefact either', () => {
    const { container } = renderReal();

    // STRUCTURAL, NOT LEXICAL - and this case is where the difference was MEASURED: the same
    // word-based negatives that pass on the fixture fail here, because the real tool
    // descriptions carry their own "ERRORS: ..." sections, so /could not|failed|error/i matches
    // the DATA. What must hold is that the component renders its two regions and nothing that
    // claims a failure or a wait.
    expect(screen.queryByRole('alert')).toBeNull();
    expect(container.querySelector('[aria-busy="true"]')).toBeNull();
    expect(screen.getAllByRole('region').map((region) => region.getAttribute('aria-labelledby'))).toEqual([
      'api-reference-routes',
      'api-reference-tools',
    ]);
  });
});
