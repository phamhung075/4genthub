import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import { SeatDetailPage } from '../../pages/SeatDetailPage';
import { seatApi } from '../../services/seatApi';
import { useWebSocket } from '../../hooks/useWebSocketV2';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
import type { SeatOverlay, SeatOverlayScope } from '../../types/seatTypes';

vi.mock('../../services/seatApi', () => ({
  seatApi: {
    listRooms: vi.fn(),
    createRoom: vi.fn(),
    listSeatTypes: vi.fn(),
    getModuleVersion: vi.fn(),
    listSeats: vi.fn(),
    createSeat: vi.fn(),
    removeSeat: vi.fn(),
    updateSeatOccupant: vi.fn(),
    putPermissionPolicy: vi.fn(),
    getOverlay: vi.fn(),
    putOverlay: vi.fn(),
    listLinks: vi.fn(),
    putLink: vi.fn(),
    deleteLink: vi.fn(),
    getSettings: vi.fn(),
    putSettings: vi.fn(),
    getResolvedSeat: vi.fn(),
  },
}));

// The page mounts the live seat sync (item 16); stub the socket and the auth context.
vi.mock('../../hooks/useWebSocketV2', () => ({
  useWebSocket: vi.fn(() => ({ client: { on: vi.fn(), off: vi.fn() }, isConnected: false })),
}));

vi.mock('../../hooks/useRealtimeSync', () => ({
  useRealtimeSync: vi.fn(),
}));

vi.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({ user: { id: 'test-user' }, tokens: { access_token: 'test-token' } }),
}));

const mockApi = vi.mocked(seatApi);

const renderDetail = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/seats/dev/alice']}>
        <Routes>
          <Route path="/seats/:room/:seat" element={<SeatDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
};

const seatTypes = [
  {
    slug: 'coder',
    name: 'Coder',
    description: 'Writes code',
    default_runtime: 'claude-code',
    latest_version: '1.0.0',
    module_refs: [{ slug: 'rules', version: '1.0.0' }],
  },
];

const seats = [
  {
    id: 'seat-1',
    room_id: 'room-1',
    seat_key: 'alice',
    seat_type: 'coder',
    pinned_version: '1.0.0',
    runtime: 'claude-code',
    model: 'sonnet',
    permission_policy: 'standard',
  },
  {
    id: 'seat-2',
    room_id: 'room-1',
    seat_key: 'bob',
    seat_type: 'coder',
    pinned_version: null,
    runtime: 'codex',
    model: 'gpt',
    permission_policy: 'standard',
  },
];

const existingOp = { kind: 'add' as const, slug: 'base', version: '1.0.0', content: '' };

const overlayFor = (scope: SeatOverlayScope, ops: SeatOverlay['ops'] = []): SeatOverlay => ({
  scope,
  ops,
});

describe('SeatDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.listSeats.mockResolvedValue({ success: true, seats });
    mockApi.listSeatTypes.mockResolvedValue({ success: true, seat_types: seatTypes });
    mockApi.getModuleVersion.mockImplementation(async (slug: string, version: string) => ({
      success: true,
      module: { slug, kind: 'instruction' as const, version, content: `${slug} content`, checksum: 'x' },
    }));
    mockApi.getOverlay.mockImplementation(async (scope: SeatOverlayScope) => ({
      success: true,
      overlay: overlayFor(scope, scope === 'seat' ? [existingOp] : []),
    }));
    mockApi.putOverlay.mockResolvedValue({ success: true, overlay: overlayFor('seat') });
    mockApi.listLinks.mockResolvedValue({
      success: true,
      links: [
        { id: 'l1', from_seat_id: 'seat-1', to_seat_id: 'seat-2', kind: 'delegates_to', allow: true },
      ],
    });
    mockApi.putLink.mockResolvedValue({
      success: true,
      link: { id: 'l1', from_seat_id: 'seat-1', to_seat_id: 'seat-2', kind: 'delegates_to', allow: false },
    });
    mockApi.getResolvedSeat.mockResolvedValue({
      success: true,
      resolved_seat: {
        room: 'dev',
        seat: 'alice',
        hash: 'abc123',
        runtime: 'claude-code',
        files: [
          { path: 'a.md', content: 'A content' },
          { path: 'b.txt', content: 'B content' },
        ],
        policy: { max_turns: 5 },
      },
    });
  });

  const openModules = async () => {
    renderDetail();
    await screen.findByText('rules');
  };

  it('keeps Add op disabled until an add or pin op carries a concrete version', async () => {
    await openModules();
    const addOp = () => screen.getByRole('button', { name: /add op/i });
    fireEvent.change(screen.getByLabelText('Module slug'), { target: { value: 'extra' } });

    fireEvent.change(screen.getByLabelText('Op kind'), { target: { value: 'add' } });
    expect(addOp()).toBeDisabled();
    fireEvent.change(screen.getByLabelText('Version'), { target: { value: '2.0.0' } });
    expect(addOp()).toBeEnabled();

    fireEvent.change(screen.getByLabelText('Version'), { target: { value: '  ' } });
    fireEvent.change(screen.getByLabelText('Op kind'), { target: { value: 'pin' } });
    expect(addOp()).toBeDisabled();

    fireEvent.change(screen.getByLabelText('Op kind'), { target: { value: 'remove' } });
    expect(addOp()).toBeEnabled();
  });

  it('builds the full ordered ops list for add, remove, override and pin and deletes an op', async () => {
    await openModules();

    // add
    fireEvent.change(screen.getByLabelText('Op kind'), { target: { value: 'add' } });
    fireEvent.change(screen.getByLabelText('Module slug'), { target: { value: 'extra' } });
    fireEvent.change(screen.getByLabelText('Version'), { target: { value: '2.0.0' } });
    fireEvent.click(screen.getByRole('button', { name: /add op/i }));
    await waitFor(() => {
      expect(mockApi.putOverlay).toHaveBeenNthCalledWith(
        1,
        'seat',
        { ops: [existingOp, { kind: 'add', slug: 'extra', version: '2.0.0', content: '' }] },
        'dev',
        'alice'
      );
    });

    // remove
    fireEvent.change(screen.getByLabelText('Op kind'), { target: { value: 'remove' } });
    fireEvent.change(screen.getByLabelText('Module slug'), { target: { value: 'base' } });
    fireEvent.click(screen.getByRole('button', { name: /add op/i }));
    await waitFor(() => {
      expect(mockApi.putOverlay).toHaveBeenNthCalledWith(
        2,
        'seat',
        { ops: [existingOp, { kind: 'remove', slug: 'base', version: '', content: '' }] },
        'dev',
        'alice'
      );
    });

    // override
    fireEvent.change(screen.getByLabelText('Op kind'), { target: { value: 'override' } });
    fireEvent.change(screen.getByLabelText('Module slug'), { target: { value: 'base' } });
    fireEvent.change(screen.getByLabelText('Content'), { target: { value: 'new content' } });
    fireEvent.click(screen.getByRole('button', { name: /add op/i }));
    await waitFor(() => {
      expect(mockApi.putOverlay).toHaveBeenNthCalledWith(
        3,
        'seat',
        { ops: [existingOp, { kind: 'override', slug: 'base', version: '', content: 'new content' }] },
        'dev',
        'alice'
      );
    });

    // pin
    fireEvent.change(screen.getByLabelText('Op kind'), { target: { value: 'pin' } });
    fireEvent.change(screen.getByLabelText('Module slug'), { target: { value: 'base' } });
    fireEvent.change(screen.getByLabelText('Version'), { target: { value: '1.2.3' } });
    fireEvent.click(screen.getByRole('button', { name: /add op/i }));
    await waitFor(() => {
      expect(mockApi.putOverlay).toHaveBeenNthCalledWith(
        4,
        'seat',
        { ops: [existingOp, { kind: 'pin', slug: 'base', version: '1.2.3', content: '' }] },
        'dev',
        'alice'
      );
    });

    // delete op 1 leaves the ordered list without it
    fireEvent.click(screen.getByLabelText('Delete op 1'));
    await waitFor(() => {
      expect(mockApi.putOverlay).toHaveBeenNthCalledWith(5, 'seat', { ops: [] }, 'dev', 'alice');
    });
  });

  it('toggles a link allow flag', async () => {
    renderDetail();
    await screen.findByText('rules');

    fireEvent.mouseDown(screen.getByRole('tab', { name: /links/i }), { button: 0 });

    const toggle = await screen.findByLabelText('Allow bob (delegates_to)');
    fireEvent.click(toggle);

    await waitFor(() => {
      expect(mockApi.putLink).toHaveBeenCalledWith('dev', 'alice', {
        to_seat: 'bob',
        kind: 'delegates_to',
        allow: false,
      });
    });
  });

  it('deletes a link after the confirmation and refetches the list', async () => {
    mockApi.deleteLink.mockResolvedValue({ success: true });
    renderDetail();
    await screen.findByText('rules');
    fireEvent.mouseDown(screen.getByRole('tab', { name: /links/i }), { button: 0 });
    expect(mockApi.listLinks).toHaveBeenCalledTimes(1);

    fireEvent.click(await screen.findByLabelText('Delete bob (delegates_to)'));
    fireEvent.click(await screen.findByRole('button', { name: 'Delete link' }));

    await waitFor(() => {
      expect(mockApi.deleteLink).toHaveBeenCalledWith('dev', 'alice', 'bob', 'delegates_to');
    });
    await waitFor(() => expect(mockApi.listLinks).toHaveBeenCalledTimes(2));
  });

  it('shows the server error when deleting a link fails', async () => {
    mockApi.deleteLink.mockRejectedValue(new Error('link alice delegates_to bob not found'));
    renderDetail();
    await screen.findByText('rules');
    fireEvent.mouseDown(screen.getByRole('tab', { name: /links/i }), { button: 0 });

    fireEvent.click(await screen.findByLabelText('Delete bob (delegates_to)'));
    fireEvent.click(await screen.findByRole('button', { name: 'Delete link' }));

    expect(await screen.findByText(/link alice delegates_to bob not found/)).toBeInTheDocument();
  });

  it('confirms what is about to be removed, and cancelling deletes nothing', async () => {
    renderDetail();
    await screen.findByText('rules');
    fireEvent.mouseDown(screen.getByRole('tab', { name: /links/i }), { button: 0 });

    fireEvent.click(await screen.findByLabelText('Delete bob (delegates_to)'));

    // The mutation waits for the confirm, and the confirm states the seat, the target, the
    // kind and the allow state as the row reads it rather than asking a bare yes/no.
    expect(mockApi.deleteLink).not.toHaveBeenCalled();
    expect(await screen.findByText('Delete this link?')).toBeInTheDocument();
    expect(
      screen.getByText('Removes the delegates_to link from alice to bob. The row currently allows it.')
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(mockApi.deleteLink).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.queryByText('Delete this link?')).not.toBeInTheDocument());
  });

  it('closes the confirmation on Escape and deletes nothing', async () => {
    renderDetail();
    await screen.findByText('rules');
    fireEvent.mouseDown(screen.getByRole('tab', { name: /links/i }), { button: 0 });

    fireEvent.click(await screen.findByLabelText('Delete bob (delegates_to)'));
    expect(await screen.findByText('Delete this link?')).toBeInTheDocument();

    fireEvent.keyDown(document, { key: 'Escape' });

    await waitFor(() => expect(screen.queryByText('Delete this link?')).not.toBeInTheDocument());
    expect(mockApi.deleteLink).not.toHaveBeenCalled();
  });

  it('shows the resolved hash and switches files', async () => {
    renderDetail();
    await screen.findByText('rules');

    fireEvent.mouseDown(screen.getByRole('tab', { name: /preview/i }), { button: 0 });

    expect(await screen.findByText('abc123')).toBeInTheDocument();
    expect(screen.getByText('A content')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'b.txt' }));

    expect(screen.getByText('B content')).toBeInTheDocument();
  });

  // The measured defect (seat-resolve row): with the local catalog lacking a referenced module the
  // resolve read fails, yet the page rendered its ordinary panels and looked healthy - the failure was
  // only visible by calling the API directly. This fails if the panels render over a failed resolve.
  it('reports a failed resolve instead of rendering the panels', async () => {
    mockApi.getResolvedSeat.mockRejectedValue(
      new Error('module queue-handoff@1.0.0 not found in catalog')
    );

    renderDetail();

    expect(await screen.findByText(/does not resolve/i)).toBeInTheDocument();
    // The reason the API gave, which names the missing reference.
    expect(
      screen.getByText('module queue-handoff@1.0.0 not found in catalog')
    ).toBeInTheDocument();
    // Nothing ordinary is rendered over it: no tabs, no resolved-snapshot panel.
    expect(screen.queryByRole('tab', { name: /modules/i })).not.toBeInTheDocument();
    expect(screen.queryByText('Resolved snapshot')).not.toBeInTheDocument();
  });

  it('offers the five OpenRig link kinds with labels and message rules', async () => {
    renderDetail();
    await screen.findByText('rules');

    fireEvent.mouseDown(screen.getByRole('tab', { name: /links/i }), { button: 0 });

    const select = (await screen.findByLabelText('Link kind')) as HTMLSelectElement;
    expect(Array.from(select.options).map(option => option.value)).toEqual([
      'delegates_to',
      'spawned_by',
      'can_observe',
      'collaborates_with',
      'escalates_to',
    ]);

    expect(screen.getByText('Gives work to')).toBeInTheDocument();
    expect(screen.getByText('Was created by')).toBeInTheDocument();
    expect(screen.getByText('Can observe')).toBeInTheDocument();
    expect(screen.getByText('Collaborates with')).toBeInTheDocument();
    expect(screen.getByText('Escalates to')).toBeInTheDocument();

    expect(screen.getByText(/never allow sending/i)).toBeInTheDocument();
  });

  describe('Permissions panel', () => {
    const openPermissions = async () => {
      renderDetail();
      await screen.findByText('rules');
      fireEvent.mouseDown(screen.getByRole('tab', { name: /permissions/i }), { button: 0 });
      return (await screen.findByLabelText('Permission policy')) as HTMLSelectElement;
    };

    it('shows the current policy, offers the five server policies and keeps Save disabled', async () => {
      const select = await openPermissions();

      expect(select.value).toBe('standard');
      expect(Array.from(select.options).map(option => option.value)).toEqual([
        'locked',
        'standard',
        'open',
        'yolo',
        'none',
      ]);
      expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
    });

    it('saves the new policy, refreshes the seats and warns about yolo', async () => {
      mockApi.putPermissionPolicy.mockResolvedValue({
        success: true,
        seat: { ...seats[0], permission_policy: 'yolo' },
      });
      const select = await openPermissions();

      fireEvent.change(select, { target: { value: 'yolo' } });
      expect(screen.getByText(/full permission bypass/)).toBeInTheDocument();
      fireEvent.click(screen.getByRole('button', { name: 'Save' }));

      await waitFor(() => {
        expect(mockApi.putPermissionPolicy).toHaveBeenCalledWith('dev', 'alice', 'yolo');
      });
      await waitFor(() => expect(mockApi.listSeats).toHaveBeenCalledTimes(2));
    });

    it('shows the API error when the policy is rejected', async () => {
      mockApi.putPermissionPolicy.mockRejectedValue(new Error('unsupported permission policy "open"'));
      const select = await openPermissions();

      fireEvent.change(select, { target: { value: 'open' } });
      fireEvent.click(screen.getByRole('button', { name: 'Save' }));

      expect(await screen.findByText(/unsupported permission policy/)).toBeInTheDocument();
    });
  });

  describe('LLM panel', () => {
    const openLlm = async () => {
      renderDetail();
      await screen.findByText('rules');
      fireEvent.mouseDown(screen.getByRole('tab', { name: /llm/i }), { button: 0 });
      return screen.findByLabelText('LLM model');
    };

    it('shows the current runtime and model and keeps Save disabled when unchanged', async () => {
      const model = (await openLlm()) as HTMLInputElement;

      expect(model.value).toBe('sonnet');
      expect((screen.getByLabelText('LLM runtime') as HTMLSelectElement).value).toBe('claude-code');
      expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
      expect(screen.getByText(/openrig_seat_sync.py switch/)).toBeInTheDocument();
    });

    it('disables Save and explains the rule when the model is invalid', async () => {
      const model = await openLlm();

      fireEvent.change(model, { target: { value: '-bad model' } });

      expect(screen.getByRole('button', { name: 'Save' })).toBeDisabled();
      expect(
        screen.getByText('Use letters, digits, ".", "_", ":", "/" or "-"; start with a letter or digit.')
      ).toBeInTheDocument();
    });

    it('saves the new runtime and model and refreshes the seats', async () => {
      mockApi.updateSeatOccupant.mockResolvedValue({
        success: true,
        seat: { ...seats[0], runtime: 'codex', model: 'gpt-5' },
      });
      const model = await openLlm();

      fireEvent.change(screen.getByLabelText('LLM runtime'), { target: { value: 'codex' } });
      fireEvent.change(model, { target: { value: 'gpt-5' } });
      fireEvent.click(screen.getByRole('button', { name: 'Save' }));

      await waitFor(() => {
        expect(mockApi.updateSeatOccupant).toHaveBeenCalledWith('dev', 'alice', {
          runtime: 'codex',
          model: 'gpt-5',
        });
      });
      await waitFor(() => expect(mockApi.listSeats).toHaveBeenCalledTimes(2));
    });

    it('allows an empty model and shows the API error on failure', async () => {
      mockApi.updateSeatOccupant.mockRejectedValue(new Error('seat is removed'));
      const model = await openLlm();

      fireEvent.change(model, { target: { value: '' } });
      fireEvent.click(screen.getByRole('button', { name: 'Save' }));

      await waitFor(() => {
        expect(mockApi.updateSeatOccupant).toHaveBeenCalledWith('dev', 'alice', {
          runtime: 'claude-code',
          model: '',
        });
      });
      expect(await screen.findByText('seat is removed')).toBeInTheDocument();
    });
  });

  describe('failed mutations', () => {
    it('shows the server error and keeps the form when adding an overlay op fails', async () => {
      mockApi.putOverlay.mockRejectedValue(new Error('module "extra" not found'));
      await openModules();

      fireEvent.change(screen.getByLabelText('Op kind'), { target: { value: 'add' } });
      fireEvent.change(screen.getByLabelText('Module slug'), { target: { value: 'extra' } });
      fireEvent.change(screen.getByLabelText('Version'), { target: { value: '2.0.0' } });
      fireEvent.click(screen.getByRole('button', { name: /add op/i }));

      expect(await screen.findByText('module "extra" not found')).toBeInTheDocument();
      expect(screen.getByLabelText('Module slug')).toHaveValue('extra');
    });

    it('shows the server error and keeps the target when adding a link fails', async () => {
      mockApi.putLink.mockRejectedValue(new Error('seat "carol" not found'));
      renderDetail();
      await screen.findByText('rules');
      fireEvent.mouseDown(screen.getByRole('tab', { name: /links/i }), { button: 0 });
      await screen.findByLabelText('Allow bob (delegates_to)');

      fireEvent.change(screen.getByLabelText('Link target'), { target: { value: 'bob' } });
      fireEvent.click(screen.getByRole('button', { name: /add link/i }));

      expect(await screen.findByText('seat "carol" not found')).toBeInTheDocument();
      expect(screen.getByLabelText('Link target')).toHaveValue('bob');
    });
  });

  it('mounts the live seat sync (useWebSocket + useRealtimeSync)', () => {
    renderDetail();

    expect(vi.mocked(useWebSocket)).toHaveBeenCalledWith('test-user', 'test-token');
    expect(vi.mocked(useRealtimeSync)).toHaveBeenCalled();
  });
});
