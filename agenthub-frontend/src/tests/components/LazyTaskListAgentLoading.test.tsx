/**
 * @fileoverview LazyTaskListRefactored loads the project agents and the user's seats
 * independently: a seat API failure keeps the project agents, flags an error for the
 * assignment dialog and is retried the next time the dialog asks for the agents.
 */

import React from 'react';
import { render, screen, act } from '@testing-library/react';
import { vi } from 'vitest';
import LazyTaskListRefactored from '../../components/LazyTaskList/LazyTaskListRefactored';
import { getAvailableAgents, listAgents } from '../../api';

vi.mock('../../api', () => ({
  getAvailableAgents: vi.fn(),
  listAgents: vi.fn(),
  getTask: vi.fn(),
}));
vi.mock('@tanstack/react-query', () => ({ useQueryClient: () => ({ fetchQuery: vi.fn() }) }));
vi.mock('../../contexts/AuthContext', () => ({ useAuth: () => ({ user: { id: 'u1' }, tokens: { access_token: 't' } }) }));
vi.mock('../../components/ui/toast', () => ({ useErrorToast: () => vi.fn() }));
vi.mock('../../hooks/useTasks', () => ({
  useTasks: () => ({ data: [], isLoading: false, refetch: vi.fn() }),
  useTaskMutations: () => ({}),
}));
vi.mock('../../hooks/useWebSocketV2', () => ({ useWebSocket: () => ({ isConnected: false, client: null }) }));
vi.mock('../../hooks/useRealtimeSync', () => ({ useRealtimeSync: vi.fn() }));

let loadAgentsOnDemand: () => Promise<void>;
vi.mock('../../components/LazyTaskList/hooks/useDialogManager', () => ({
  useDialogManager: (_p: string, _t: string, _u: unknown, _s: unknown, _l: unknown, load: () => Promise<void>) => {
    loadAgentsOnDemand = load;
    return {
      activeDialog: { type: null },
      openDialog: vi.fn(),
      closeDialog: vi.fn(),
      saving: false,
      setSaving: vi.fn(),
      isClosingRef: { current: false },
    };
  },
}));
vi.mock('../../components/LazyTaskList/components', () => ({
  TaskListHeader: () => null,
  TaskListContent: () => null,
  TaskSearchSection: () => null,
  DialogSection: ({ agents, availableAgents, availableAgentsError }: any) => (
    <div
      data-testid="sections"
      data-project-agents={agents.length}
      data-seats={availableAgents.join(',')}
      data-error={String(availableAgentsError)}
    />
  ),
}));

const sections = () => screen.getByTestId('sections');

describe('LazyTaskListRefactored agent loading', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
    vi.mocked(listAgents).mockResolvedValue([{ id: 'a1' }, { id: 'a2' }]);
    vi.mocked(getAvailableAgents).mockResolvedValue(['@lead']);
    render(<LazyTaskListRefactored projectId="p1" taskTreeId="b1" />);
  });

  it('hands both lists over without an error', async () => {
    await act(async () => loadAgentsOnDemand());

    expect(sections()).toHaveAttribute('data-project-agents', '2');
    expect(sections()).toHaveAttribute('data-seats', '@lead');
    expect(sections()).toHaveAttribute('data-error', 'false');
  });

  it('keeps the project agents and flags an error when the seat API fails', async () => {
    vi.mocked(getAvailableAgents).mockRejectedValue(new Error('seat API down'));

    await act(async () => loadAgentsOnDemand());

    expect(sections()).toHaveAttribute('data-project-agents', '2');
    expect(sections()).toHaveAttribute('data-seats', '');
    expect(sections()).toHaveAttribute('data-error', 'true');
  });

  it('keeps the seats when the project agents fail to load', async () => {
    vi.mocked(listAgents).mockRejectedValue(new Error('agents down'));

    await act(async () => loadAgentsOnDemand());

    expect(sections()).toHaveAttribute('data-seats', '@lead');
    expect(sections()).toHaveAttribute('data-error', 'false');
  });

  it('retries after a failure and clears the error', async () => {
    vi.mocked(getAvailableAgents).mockRejectedValueOnce(new Error('seat API down'));
    await act(async () => loadAgentsOnDemand());
    expect(sections()).toHaveAttribute('data-error', 'true');

    await act(async () => loadAgentsOnDemand());

    expect(getAvailableAgents).toHaveBeenCalledTimes(2);
    expect(sections()).toHaveAttribute('data-seats', '@lead');
    expect(sections()).toHaveAttribute('data-error', 'false');
  });

  it('does not load again once both lists are in', async () => {
    await act(async () => loadAgentsOnDemand());
    await act(async () => loadAgentsOnDemand());

    expect(getAvailableAgents).toHaveBeenCalledTimes(1);
    expect(listAgents).toHaveBeenCalledTimes(1);
  });
});
