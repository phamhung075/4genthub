/**
 * ApiReferenceView - the docs page's reference tier, driven rather than described.
 *
 * The cases pin the three properties that make this component honest: it renders every entry
 * it is given (no hand-typed list), it renders the two LEGITIMATE EMPTIES as absent rather
 * than as an error or a placeholder, and it carries no loading or failure state at all
 * because a build-time import has no runtime load to fail.
 *
 * The reference prop is REQUIRED, which is a compile-time contract rather than a runtime one:
 * an absent reference fails `tsc` at the caller, so no case here asserts a missing prop.
 */

import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { ApiReferenceView } from '../../components/docs/ApiReferenceView';
import type { ApiReference } from '../../types/apiReference';

const toolsParameters = {
  type: 'object',
  properties: {
    action: { type: 'string' },
    project_id: { type: 'string' },
  },
  required: ['action'],
};

const reference: ApiReference = {
  routes: [
    {
      method: 'GET',
      path: '/api/v2/openrig/rooms',
      pathParams: [],
      handler: 'handleListRooms',
      description: 'Lists the rooms the caller owns.',
    },
    {
      method: 'DELETE',
      path: '/api/v2/openrig/rooms/{room}/seats/{seat}/links/{to}/{kind}',
      pathParams: ['room', 'seat', 'to', 'kind'],
      // An inline closure: the generator emits no handler name, and this is LEGITIMATE.
      handler: '',
      description: '',
    },
  ],
  tools: [
    {
      name: 'manage_project',
      description: 'Project lifecycle.',
      actions: ['list', 'create'],
      parameters: toolsParameters,
    },
    {
      name: 'call_seat',
      description: '',
      // A tool with no action parameter: an empty array, not a failure.
      actions: [],
      parameters: { type: 'object', additionalProperties: false },
    },
  ],
};

const renderView = (value: ApiReference = reference) => render(<ApiReferenceView reference={value} />);

const routesRegion = () => screen.getByRole('region', { name: 'HTTP routes' });
const toolsRegion = () => screen.getByRole('region', { name: 'MCP tools' });

describe('ApiReferenceView', () => {
  it('renders every route the reference carries, with its method, path and handler', () => {
    renderView();

    expect(within(routesRegion()).getByText('2 routes, generated from the mounts rather than typed by hand.')).toBeInTheDocument();
    expect(within(routesRegion()).getByText('/api/v2/openrig/rooms')).toBeInTheDocument();
    expect(within(routesRegion()).getByText('handleListRooms')).toBeInTheDocument();
    expect(within(routesRegion()).getByText('Lists the rooms the caller owns.')).toBeInTheDocument();
    expect(
      within(routesRegion()).getByText('/api/v2/openrig/rooms/{room}/seats/{seat}/links/{to}/{kind}')
    ).toBeInTheDocument();
  });

  // The generator emits an empty handler when a mount registers an inline closure. That is a
  // state, not a gap: the row must render as absent rather than as a placeholder claiming
  // something the data does not say.
  it('renders an inline closure as absent - the row carries nothing but its method and path', () => {
    renderView();

    const row = within(routesRegion())
      .getByText('/api/v2/openrig/rooms/{room}/seats/{seat}/links/{to}/{kind}')
      .closest('li') as HTMLElement;

    expect(row.textContent?.replace(/\s+/g, '')).toBe(
      'DELETE/api/v2/openrig/rooms/{room}/seats/{seat}/links/{to}/{kind}'
    );
    expect(row.querySelector('p')).toBeNull();
  });

  it("renders a tool's actions only when it declares them", () => {
    renderView();

    const withActions = within(toolsRegion()).getByRole('article', { name: 'manage_project' });
    expect(within(withActions).getByText('Actions')).toBeInTheDocument();
    expect(within(withActions).getByText('list')).toBeInTheDocument();
    expect(within(withActions).getByText('create')).toBeInTheDocument();

    const withoutActions = within(toolsRegion()).getByRole('article', { name: 'call_seat' });
    // No badge NODE exists either: `Badge` renders a span, so this asserts the absence rather
    // than inheriting it from a map over an empty array (fe-dev's precision note - a reader
    // checking the claim should read the test and not only the component).
    expect(withoutActions.querySelectorAll('span')).toHaveLength(0);
    expect(within(withoutActions).queryByText('Actions')).toBeNull();
    // It declares no description either, so the only paragraph is the Parameters label: an
    // empty description adds no element at all, rather than an empty one.
    expect(withoutActions.querySelectorAll('p')).toHaveLength(1);
    expect(withActions.querySelectorAll('p')).toHaveLength(2);
  });

  // The page must not become a second source of truth about a shape: the block is the server's
  // own schema, character for character.
  it("renders the parameter schema verbatim - it parses back to the object the reference carries", () => {
    renderView();

    const article = within(toolsRegion()).getByRole('article', { name: 'manage_project' });
    const block = article.querySelector('pre') as HTMLElement;

    expect(JSON.parse(block.textContent ?? '')).toEqual(toolsParameters);
  });

  it('derives the property summary from that same schema, and marks only what the schema marks', () => {
    renderView();

    const article = within(toolsRegion()).getByRole('article', { name: 'manage_project' });
    const action = within(article).getByText('action').closest('li') as HTMLElement;
    const projectId = within(article).getByText('project_id').closest('li') as HTMLElement;

    expect(within(action).getByText('string')).toBeInTheDocument();
    expect(within(action).getByText('required')).toBeInTheDocument();
    // Not required, and the schema says so - the page must not infer it.
    expect(within(projectId).getByText('string')).toBeInTheDocument();
    expect(within(projectId).queryByText('required')).toBeNull();

    // A schema with no properties yields no summary rows rather than an empty list rendered.
    const bare = within(toolsRegion()).getByRole('article', { name: 'call_seat' });
    expect(within(bare).queryByText('Parameters')).toBeInTheDocument();
    expect(bare.querySelectorAll('ul li')).toHaveLength(0);
  });

  // The reference arrives through a build-time import, so there is no runtime load to fail and
  // no loading state to show. A branch for either would be unreachable code.
  it('carries no loading state and no failure state', () => {
    renderView();

    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.queryByText(/loading/i)).toBeNull();
    expect(screen.queryByText(/could not|failed|error/i)).toBeNull();
  });

  it('renders a reference with no routes and no tools as empty sections rather than as a failure', () => {
    renderView({ routes: [], tools: [] });

    expect(within(routesRegion()).getByText('0 routes, generated from the mounts rather than typed by hand.')).toBeInTheDocument();
    expect(within(toolsRegion()).getByText('0 tools, with the parameters the server advertises.')).toBeInTheDocument();
    expect(screen.queryByRole('alert')).toBeNull();
  });
});
