import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { vi } from 'vitest';
import { RoomDecisionPanel } from '../../components/RoomDecisionPanel';
import { seatApi } from '../../services/seatApi';
import { decisionApi } from '../../services/decisionApi';
import { renderWithQuery } from '../query-utils';
import type { RoomDecision } from '../../types/seatTypes';

/**
 * The panel's contract, from the frozen lane-1 design (2026-10-12): options are rendered from the
 * stored questions verbatim, one answer is posted per question, a row that is only `answered` stays
 * in the list because the daemon has not applied it, a closed row does not, and both a refusal and
 * an unreadable list are shown rather than swallowed.
 *
 * The SERVICES are mocked, so the real hooks (query keys, `enabled`, invalidation) run: what this
 * file pins is the panel's behaviour and the (room, decision, question, option) payload it sends.
 * The route itself is verified against the running server when go-dev's slice lands.
 */

vi.mock('../../services/seatApi', () => ({
  seatApi: { listRooms: vi.fn() },
}));

vi.mock('../../services/decisionApi', () => ({
  decisionApi: { listRoomDecisions: vi.fn(), answerRoomDecision: vi.fn() },
}));

const listRooms = vi.mocked(seatApi.listRooms);
const listRoomDecisions = vi.mocked(decisionApi.listRoomDecisions);
const answerRoomDecision = vi.mocked(decisionApi.answerRoomDecision);

const question = {
  id: 'q1',
  question: 'Ship the sidebar now?',
  options: [
    { id: 'yes', label: 'Yes, ship it' },
    { id: 'no', label: 'No, hold it', recommended: true },
  ],
};

const decision = (overrides: Partial<RoomDecision> = {}): RoomDecision => ({
  id: 'd1',
  qitem_id: 'qi-1',
  author_seat_key: '4genthub-min.lead',
  summary: 'Ship the sidebar?',
  detail: 'Two sections, the lower one answers.',
  questions: [question],
  answers: {},
  state: 'pending',
  created_at: '2026-10-12T18:03:00Z',
  answered_at: null,
  ...overrides,
});

/** The URL names the room, so the panel reads that room without a pick. */
const renderPanel = () =>
  renderWithQuery(
    <MemoryRouter initialEntries={['/seats/dev/go-dev']}>
      <RoomDecisionPanel />
    </MemoryRouter>
  );

beforeEach(() => {
  vi.clearAllMocks();
  listRooms.mockResolvedValue({ rooms: [{ id: 'r1', slug: 'dev', name: 'Dev', team_id: '', role: 'owner' }] });
  listRoomDecisions.mockResolvedValue({ decisions: [decision()] });
  answerRoomDecision.mockResolvedValue({ state: 'answered', answers: { q1: 'no' }, complete: false });
});

it('renders the stored questions and their options verbatim for the room in the URL', async () => {
  renderPanel();

  expect(await screen.findByText('Ship the sidebar now?')).toBeInTheDocument();
  expect(screen.getByText('Yes, ship it')).toBeInTheDocument();
  expect(screen.getByText('No, hold it')).toBeInTheDocument();
  expect(screen.getByText(/4genthub-min\.lead/)).toBeInTheDocument();
  expect(screen.getByText('waiting for you')).toBeInTheDocument();
  expect(listRoomDecisions).toHaveBeenCalledWith('dev');
});

it('posts one answer per question with the chosen option', async () => {
  renderPanel();
  await screen.findByText('No, hold it');

  fireEvent.click(screen.getByText('No, hold it'));
  await waitFor(() => expect(screen.getByRole('button', { name: /send answer/i })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: /send answer/i }));

  await waitFor(() =>
    expect(answerRoomDecision).toHaveBeenCalledWith('dev', 'd1', { question_id: 'q1', option_id: 'no' })
  );
});

it('keeps an answered row in the list and drops a closed one', async () => {
  listRoomDecisions.mockResolvedValue({
    decisions: [
      decision({ id: 'd1', state: 'answered', answers: { q1: 'no' } }),
      decision({ id: 'd2', summary: 'Closed elsewhere', state: 'resolved' }),
    ],
  });
  renderPanel();

  expect(await screen.findByText('awaiting the room')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: /answer recorded/i })).toBeDisabled();
  expect(screen.queryByText('Closed elsewhere')).not.toBeInTheDocument();
});

it('shows a refused answer instead of a silent no-op', async () => {
  answerRoomDecision.mockRejectedValue(new Error('not-the-asked-human'));
  renderPanel();
  await screen.findByText('No, hold it');

  fireEvent.click(screen.getByText('No, hold it'));
  await waitFor(() => expect(screen.getByRole('button', { name: /send answer/i })).toBeEnabled());
  fireEvent.click(screen.getByRole('button', { name: /send answer/i }));

  expect(await screen.findByRole('alert')).toHaveTextContent('not-the-asked-human');
});

it("shows why the room's list could not be read", async () => {
  // The message the browser really produced on the OF4 local stack for the absent route: the status
  // is part of it now, so the operator can tell a missing route from a refused answer.
  listRoomDecisions.mockRejectedValue(new Error('Request failed: HTTP 404'));
  renderPanel();

  expect(await screen.findByRole('alert')).toHaveTextContent('Request failed: HTTP 404');
});
