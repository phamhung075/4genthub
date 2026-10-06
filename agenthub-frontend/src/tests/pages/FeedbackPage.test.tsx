/**
 * Seat Friction Page (Directive H, read side).
 *
 * The cases drive the rendered page rather than the grouping helper: the deliverable is
 * that the six layers appear in canonical order with each report under its own layer, and
 * that a layer the response omits says "nothing reported" instead of disappearing.
 */

import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import { FeedbackPage } from '../../pages/FeedbackPage';
import { feedbackApi } from '../../services/feedbackApi';
import type { FeedbackLayerGroup, FeedbackReport } from '../../types/feedback';

vi.mock('../../services/feedbackApi', () => ({
  feedbackApi: { listFeedback: vi.fn() },
}));

const mockApi = vi.mocked(feedbackApi);

const report = (over: Partial<FeedbackReport> & Pick<FeedbackReport, 'id' | 'layer' | 'text'>): FeedbackReport => ({
  room: 'of4room',
  seat: 'alpha',
  session: '4genthub-min-web-dev@4genthub-min',
  created_at: '2026-10-06T16:40:00Z',
  machine_id: '',
  ...over,
});

const group = (
  layer: FeedbackLayerGroup['layer'],
  reports: FeedbackReport[],
  count = reports.length
): FeedbackLayerGroup => ({ layer, count, reports });

const renderPage = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <FeedbackPage />
    </QueryClientProvider>
  );
};

const sectionFor = async (label: string) => {
  const heading = await screen.findByRole('heading', { level: 2, name: label });
  return heading.closest('section') as HTMLElement;
};

describe('FeedbackPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all six layers in the canonical order and each report under its own layer', async () => {
    mockApi.listFeedback.mockResolvedValue({
      success: true,
      total: 3,
      // The API's order, and one layer deliberately absent from the array.
      layers: [
        group('cloud', [report({ id: 'c1', layer: 'cloud', text: 'the token route answers 403' })]),
        group('runtime', [
          report({ id: 'r1', layer: 'runtime', text: 'the seat could not ask for permission' }),
          report({ id: 'r2', layer: 'runtime', text: 'the tool list came back empty' }),
        ]),
      ],
    });

    renderPage();

    await screen.findByRole('heading', { level: 2, name: 'Runtime' });
    expect(screen.getAllByRole('heading', { level: 2 }).map((h) => h.textContent)).toEqual([
      'Runtime',
      'OpenRig',
      'Cloud',
      'Seat context',
      'Workspace',
      'Other',
    ]);

    const runtime = await sectionFor('Runtime');
    expect(within(runtime).getByText('the seat could not ask for permission')).toBeInTheDocument();
    expect(within(runtime).getByText('the tool list came back empty')).toBeInTheDocument();
    expect(within(runtime).queryByText('the token route answers 403')).not.toBeInTheDocument();

    const cloud = await sectionFor('Cloud');
    expect(within(cloud).getByText('the token route answers 403')).toBeInTheDocument();
    expect(
      within(cloud).queryByText('the seat could not ask for permission')
    ).not.toBeInTheDocument();

    expect(screen.getByText('3 entries, grouped by the layer it was reported against.')).toBeInTheDocument();
    expect(mockApi.listFeedback).toHaveBeenCalledTimes(1);
  });

  it('says nothing was reported for a layer the response omits, rather than hiding the layer', async () => {
    mockApi.listFeedback.mockResolvedValue({
      success: true,
      total: 1,
      layers: [group('workspace', [report({ id: 'w1', layer: 'workspace', text: 'the build flaked' })])],
    });

    renderPage();

    const workspace = await sectionFor('Workspace');
    expect(within(workspace).getByText('the build flaked')).toBeInTheDocument();
    expect(within(workspace).queryByText('Nothing reported for this layer.')).not.toBeInTheDocument();

    // The other five headings stay, each with its own empty state.
    for (const label of ['Runtime', 'OpenRig', 'Cloud', 'Seat context', 'Other']) {
      const section = await sectionFor(label);
      expect(within(section).getByText('Nothing reported for this layer.')).toBeInTheDocument();
    }
  });

  it('shows the whole-table empty state with the grouping still visible', async () => {
    mockApi.listFeedback.mockResolvedValue({ success: true, total: 0, layers: [] });

    renderPage();

    expect(await screen.findByText('No friction entries reported yet.')).toBeInTheDocument();
    expect(screen.getByText('0 entries, grouped by the layer it was reported against.')).toBeInTheDocument();
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(6);
  });

  // The worst failure this page can have is a false statement that looks true: "nothing
  // reported for this layer" is the SERVER's claim, and a failed read cannot make it.
  it('does not claim a layer is empty when the read has never succeeded', async () => {
    mockApi.listFeedback.mockRejectedValue(new Error('Not authenticated'));

    renderPage();

    expect(
      await screen.findByText('Could not load the friction entries: Not authenticated')
    ).toBeInTheDocument();
    expect(
      screen.getAllByText('Not loaded: the read failed, so this layer’s count is unknown.')
    ).toHaveLength(6);
    expect(screen.queryByText('Nothing reported for this layer.')).not.toBeInTheDocument();
    expect(screen.queryByText('No friction entries reported yet.')).not.toBeInTheDocument();
    // And no count is stated as if it were known.
    expect(screen.getByText('Counts unavailable: the read has not succeeded.')).toBeInTheDocument();
    expect(screen.queryByText(/entries, grouped by the layer/)).not.toBeInTheDocument();
  });

  it('keeps the last successful read visible when a refresh fails, and says which it is', async () => {
    mockApi.listFeedback.mockResolvedValue({
      success: true,
      total: 1,
      layers: [group('cloud', [report({ id: 'c1', layer: 'cloud', text: 'the token route answers 403' })])],
    });

    renderPage();

    expect(within(await sectionFor('Cloud')).getByText('the token route answers 403')).toBeInTheDocument();

    mockApi.listFeedback.mockRejectedValue(new Error('Request failed'));
    fireEvent.click(screen.getByRole('button', { name: /Refresh/ }));

    expect(
      await screen.findByText(
        'Could not refresh the friction entries: Request failed The groups below are the last read that succeeded.'
      )
    ).toBeInTheDocument();
    // The rows from the successful read stay, and the header still states what it knows.
    expect(within(await sectionFor('Cloud')).getByText('the token route answers 403')).toBeInTheDocument();
    expect(
      screen.getByText('1 entry, grouped by the layer it was reported against.')
    ).toBeInTheDocument();
  });

  it('renders the row fields the contract states, without interpreting them', async () => {
    mockApi.listFeedback.mockResolvedValue({
      success: true,
      total: 1,
      layers: [
        group('openrig', [
          report({
            id: 'o1',
            layer: 'openrig',
            text: 'the seat never came back after a restart',
            room: 'dev',
            seat: 'beta',
            session: '',
            created_at: '2026-10-06T15:17:31Z',
            machine_id: 'bridge-7',
          }),
        ]),
      ],
    });

    renderPage();

    const section = await sectionFor('OpenRig');
    expect(within(section).getByText('2026-10-06T15:17:31Z')).toBeInTheDocument();
    expect(within(section).getByText('dev/beta')).toBeInTheDocument();
    expect(within(section).getByText('bridge-7')).toBeInTheDocument();
    expect(within(section).getByText('the seat never came back after a restart')).toBeInTheDocument();
  });

  it('offers no control but Refresh - a viewer, not a workflow', async () => {
    mockApi.listFeedback.mockResolvedValue({
      success: true,
      total: 1,
      layers: [group('other', [report({ id: 'x1', layer: 'other', text: 'unclassifiable' })])],
    });

    renderPage();

    await screen.findByRole('heading', { level: 2, name: 'Other' });
    const buttons = screen.getAllByRole('button');
    expect(buttons.map((button) => button.textContent?.trim())).toEqual(['Refresh']);
    expect(screen.queryByRole('checkbox')).not.toBeInTheDocument();
    expect(screen.queryByRole('combobox')).not.toBeInTheDocument();
  });

  it('shows a group the closed set does not define rather than filing it elsewhere', async () => {
    mockApi.listFeedback.mockResolvedValue({
      success: true,
      total: 1,
      layers: [
        group('cosmos' as FeedbackLayerGroup['layer'], [
          report({ id: 'u1', layer: 'cosmos' as FeedbackReport['layer'], text: 'from outside the set' }),
        ]),
      ],
    });

    renderPage();

    expect(await screen.findByText(/Unrecognised layer:/)).toBeInTheDocument();
    expect(screen.getByText('cosmos')).toBeInTheDocument();
    expect(screen.getByText('from outside the set')).toBeInTheDocument();
    // The closed set's own headings are all still there and all empty.
    expect(screen.getAllByRole('heading', { level: 2 })).toHaveLength(7);
  });

  it('re-runs the same read when Refresh is pressed', async () => {
    mockApi.listFeedback.mockResolvedValue({ success: true, total: 0, layers: [] });

    renderPage();

    // The button is disabled while the first read is in flight, so wait for the loaded
    // state before clicking - otherwise the click lands on a disabled control and the
    // count stays at one for a reason that has nothing to do with Refresh.
    const refresh = await screen.findByRole('button', { name: /Refresh/ });
    await screen.findByText('No friction entries reported yet.');
    fireEvent.click(refresh);

    await waitFor(() => expect(mockApi.listFeedback).toHaveBeenCalledTimes(2));
  });
});
