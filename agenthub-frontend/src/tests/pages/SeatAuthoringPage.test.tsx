import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { vi } from 'vitest';
import { SeatAuthoringPage } from '../../pages/SeatAuthoringPage';
import { seatApi } from '../../services/seatApi';
import { useWebSocket } from '../../hooks/useWebSocketV2';
import { useRealtimeSync } from '../../hooks/useRealtimeSync';
import type { SeatOverlayOp, SeatOverlayScope } from '../../types/seatTypes';

vi.mock('../../services/seatApi', () => ({
  seatApi: {
    listSeatTypes: vi.fn(),
    listModules: vi.fn(),
    putModuleVersion: vi.fn(),
    createSeatTypeVersion: vi.fn(),
    listRooms: vi.fn(),
    listSeats: vi.fn(),
    getOverlay: vi.fn(),
    putOverlay: vi.fn(),
    getModuleVersion: vi.fn(),
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

const renderPage = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SeatAuthoringPage />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

const seatType = {
  slug: 'coder',
  name: 'Coder',
  description: 'Writes code',
  default_runtime: 'claude-code',
  latest_version: '1.0.0',
  module_refs: [{ slug: 'rules', version: '1.0.0' }],
};

const fill = (label: string, value: string) =>
  fireEvent.change(screen.getByLabelText(label), { target: { value } });

describe('SeatAuthoringPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockApi.listSeatTypes.mockResolvedValue({ success: true, seat_types: [seatType] });
    mockApi.listModules.mockResolvedValue({
      success: true,
      modules: [{ slug: 'rules', kind: 'instruction', version: '1.0.0', sha256: 'abcdef0123456789' }],
    });
    mockApi.createSeatTypeVersion.mockResolvedValue({
      success: true,
      seat_type_version: {
        slug: 'coder',
        version: '1.0.1',
        default_runtime: 'codex',
        module_refs: [{ slug: 'rules', version: '1.0.0' }],
      },
    });
    mockApi.putModuleVersion.mockResolvedValue({
      success: true,
      module: { slug: 'rules', kind: 'instruction', version: '1.1.0', sha256: 'abc' },
    });
    mockApi.listRooms.mockResolvedValue({
      success: true,
      rooms: [{ id: 'room-dev', slug: 'dev', name: 'Dev Room' }],
    });
    mockApi.listSeats.mockResolvedValue({
      success: true,
      seats: [
        {
          id: 'seat-1',
          room_id: 'room-dev',
          seat_key: 'alice',
          seat_type: 'coder',
          seat_type_id: 'type-1',
          pinned_version: '1.0.0',
          runtime: 'claude-code',
          model: '',
          permission_policy: 'standard',
        },
      ],
    });
    mockApi.getOverlay.mockImplementation(async (scope) => ({
      success: true,
      overlay: { scope, ops: [] },
    }));
    mockApi.putOverlay.mockResolvedValue({ success: true, overlay: { scope: 'seat', ops: [] } });
    mockApi.getModuleVersion.mockImplementation(async (slug) => ({
      success: true,
      module: {
        slug,
        kind: 'mcp',
        version: '1.0.0',
        checksum: 'sum',
        content:
          slug === 'agenthub-http'
            ? JSON.stringify({ name: 'agenthub_http', type: 'http', url: 'https://mcp.test', headers: {} })
            : JSON.stringify({ name: 'sequential-thinking', type: 'stdio', command: 'npx', args: ['-y', 'pkg'] }),
      },
    }));
  });

  it('lists seat types with their default runtime and module refs', async () => {
    renderPage();

    const card = (await screen.findByText('Coder')).closest('div.rounded-md') as HTMLElement;
    expect(within(card).getByText('claude-code')).toBeInTheDocument();
    expect(within(card).getByText('rules@1.0.0')).toBeInTheDocument();
  });

  // An mcp module's content is ONE server block the renderer parses, and the publish route checks the
  // KIND rather than the block - measured on the running backend: `{"kind":"mcp","content":"not a
  // block"}` is accepted with 200. So the form refuses the plain-text shape here, instead of letting
  // some seat's resolve refuse it later and look like a broken seat.
  it('refuses mcp content that is not one server block, and accepts a block', async () => {
    renderPage();
    fireEvent.change(await screen.findByLabelText('Module kind'), { target: { value: 'mcp' } });
    fireEvent.change(screen.getByLabelText('Module slug'), { target: { value: 'probe-block' } });
    fireEvent.change(screen.getByLabelText('Module version'), { target: { value: '1.0.0' } });
    fireEvent.change(screen.getByLabelText('Module content'), {
      target: { value: 'rule: do the thing' },
    });

    expect(screen.getByRole('button', { name: 'Publish' })).toBeDisabled();
    expect(screen.getByText(/Not a server block/)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Module content'), {
      target: { value: JSON.stringify({ name: 'probe', type: 'stdio', command: 'npx' }) },
    });

    expect(screen.queryByText(/Not a server block/)).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Publish' })).toBeEnabled();
  });

  it('keeps Publish disabled until slug, version and content are valid', async () => {
    renderPage();
    await screen.findByText('Coder');
    const publish = screen.getByRole('button', { name: 'Publish' });

    expect(publish).toBeDisabled();

    fill('Module slug', 'Bad Slug');
    fill('Module version', '1.0');
    fill('Module content', 'text');
    expect(publish).toBeDisabled();
    expect(screen.getByText(/lowercase letters/)).toBeInTheDocument();
    expect(screen.getByText(/concrete semver/)).toBeInTheDocument();

    fill('Module slug', 'rules');
    fill('Module version', '1.1.0');
    expect(publish).toBeEnabled();
  });

  it('publishes a module version and clears the form', async () => {
    renderPage();
    await screen.findByText('Coder');

    fill('Module slug', 'rules');
    fill('Module version', '1.1.0');
    fireEvent.change(screen.getByLabelText('Module kind'), { target: { value: 'document' } });
    fill('Module content', 'Be precise.');
    fireEvent.click(screen.getByRole('button', { name: 'Publish' }));

    await waitFor(() =>
      expect(mockApi.putModuleVersion).toHaveBeenCalledWith('rules', '1.1.0', {
        kind: 'document',
        content: 'Be precise.',
      })
    );
    await waitFor(() => expect(screen.getByLabelText('Module slug')).toHaveValue(''));
  });

  it('shows the server error when the version already exists', async () => {
    mockApi.putModuleVersion.mockRejectedValue(
      new Error('version 1.0.0 of module rules already exists with different content')
    );
    renderPage();
    await screen.findByText('Coder');

    fill('Module slug', 'rules');
    fill('Module version', '1.0.0');
    fill('Module content', 'changed');
    fireEvent.click(screen.getByRole('button', { name: 'Publish' }));

    expect(await screen.findByText(/already exists with different content/)).toBeInTheDocument();
    expect(screen.getByLabelText('Module slug')).toHaveValue('rules');
  });

  it('lists the latest version of each module', async () => {
    renderPage();

    const row = (await screen.findByText('abcdef01')).closest('div.rounded-md') as HTMLElement;
    expect(within(row).getByText('rules')).toBeInTheDocument();
    expect(within(row).getByText('instruction')).toBeInTheDocument();
    expect(within(row).getByText('1.0.0')).toBeInTheDocument();
  });

  it('creates a seat type version from the selected type, prefilled and editable', async () => {
    renderPage();
    await screen.findByText('abcdef01');

    fireEvent.change(screen.getByLabelText('Seat type'), { target: { value: 'coder' } });
    expect(screen.getByLabelText('Module refs')).toHaveValue('rules@1.0.0');

    fireEvent.change(screen.getByLabelText('Default runtime'), { target: { value: 'codex' } });
    fill('Module refs', 'rules@1.0.0\nstyle@2.1.0');
    fireEvent.click(screen.getByRole('button', { name: 'Create version' }));

    await waitFor(() =>
      expect(mockApi.createSeatTypeVersion).toHaveBeenCalledWith('coder', {
        module_refs: ['rules@1.0.0', 'style@2.1.0'],
        default_runtime: 'codex',
      })
    );
  });

  it('rejects malformed and duplicate module refs before sending', async () => {
    renderPage();
    await screen.findByText('abcdef01');
    fireEvent.change(screen.getByLabelText('Seat type'), { target: { value: 'coder' } });
    const create = screen.getByRole('button', { name: 'Create version' });

    fill('Module refs', 'rules@latest');
    expect(create).toBeDisabled();
    expect(screen.getByText(/no "latest"/)).toBeInTheDocument();

    fill('Module refs', 'rules@1.0.0\nrules@1.1.0');
    expect(create).toBeDisabled();
    expect(screen.getByText(/only once/)).toBeInTheDocument();

    fill('Module refs', '');
    expect(create).toBeEnabled();
  });

  it('disables Publish for empty content and for content over the size limit', async () => {
    renderPage();
    await screen.findByText('Coder');
    fill('Module slug', 'rules');
    fill('Module version', '1.1.0');
    const publish = screen.getByRole('button', { name: 'Publish' });

    expect(publish).toBeDisabled();

    fill('Module content', 'x'.repeat(65537));
    expect(publish).toBeDisabled();
    expect(screen.getByText(/limit is 65536/)).toBeInTheDocument();

    fill('Module content', 'x'.repeat(65536));
    expect(publish).toBeEnabled();
  });

  it('shows the server error when creating a seat type version fails', async () => {
    mockApi.createSeatTypeVersion.mockRejectedValue(new Error('module "style" version 2.1.0 does not exist'));
    renderPage();
    await screen.findByText('abcdef01');
    fireEvent.change(screen.getByLabelText('Seat type'), { target: { value: 'coder' } });
    fill('Module refs', 'style@2.1.0');
    fireEvent.click(screen.getByRole('button', { name: 'Create version' }));

    expect(await screen.findByText(/does not exist/)).toBeInTheDocument();
    expect(screen.getByLabelText('Module refs')).toHaveValue('style@2.1.0');
  });

  it('refetches the module and seat type lists after a successful publish and create', async () => {
    renderPage();
    await screen.findByText('abcdef01');
    expect(mockApi.listModules).toHaveBeenCalledTimes(1);

    fill('Module slug', 'rules');
    fill('Module version', '1.1.0');
    fill('Module content', 'Be precise.');
    fireEvent.click(screen.getByRole('button', { name: 'Publish' }));
    await waitFor(() => expect(mockApi.listModules).toHaveBeenCalledTimes(2));

    fireEvent.change(screen.getByLabelText('Seat type'), { target: { value: 'coder' } });
    fireEvent.click(screen.getByRole('button', { name: 'Create version' }));
    await waitFor(() => expect(mockApi.listSeatTypes).toHaveBeenCalledTimes(2));
  });

  it('prefills the first runtime for a seat type that has no version yet', async () => {
    mockApi.listSeatTypes.mockResolvedValue({
      success: true,
      seat_types: [{ ...seatType, default_runtime: null, latest_version: null, module_refs: [] }],
    });
    renderPage();
    await screen.findByText('no version');
    expect(screen.getByText('no runtime')).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Seat type'), { target: { value: 'coder' } });

    expect(screen.getByLabelText('Default runtime')).toHaveValue('claude-code');
    expect(screen.getByLabelText('Module refs')).toHaveValue('');
  });

  it('mounts the live seat sync (useWebSocket + useRealtimeSync)', () => {
    renderPage();

    expect(vi.mocked(useWebSocket)).toHaveBeenCalledWith('test-user', 'test-token');
    expect(vi.mocked(useRealtimeSync)).toHaveBeenCalled();
  });
});

describe('SeatAuthoringPage composer', () => {
  const overlaysFor = (ops: Partial<Record<SeatOverlayScope, SeatOverlayOp[]>>) => {
    mockApi.getOverlay.mockImplementation(async (scope) => ({
      success: true,
      overlay: { scope, ops: ops[scope] ?? [] },
    }));
  };

  // The composer needs rooms and seats to resolve before it renders.
  const openComposer = async () => {
    renderPage();
    return screen.findByLabelText('Compose level');
  };

  it('labels each block with where it is inherited from and what removing it here does', async () => {
    overlaysFor({ company: [{ kind: 'add', slug: 'style', version: '2.0.0', content: '' }] });
    await openComposer();

    const blocks = await screen.findByRole('list', { name: 'Composed blocks' });
    expect(within(blocks).getByText('rules@1.0.0')).toBeInTheDocument();
    expect(within(blocks).getByText('inherited from the seat type')).toBeInTheDocument();
    expect(within(blocks).getByText('style@2.0.0')).toBeInTheDocument();
    expect(within(blocks).getByText('inherited from company')).toBeInTheDocument();
    expect(
      within(blocks).getByText('Removing here: removed at seat · still defined at company')
    ).toBeInTheDocument();
  });

  it('removes an inherited block by writing one remove op at this level', async () => {
    overlaysFor({ company: [{ kind: 'add', slug: 'style', version: '2.0.0', content: '' }] });
    await openComposer();

    const blocks = await screen.findByRole('list', { name: 'Composed blocks' });
    const row = within(blocks).getByText('style@2.0.0').closest('li') as HTMLElement;
    fireEvent.click(within(row).getByRole('button', { name: /Remove here/ }));

    await waitFor(() =>
      expect(mockApi.putOverlay).toHaveBeenCalledWith(
        'seat',
        { ops: [{ kind: 'remove', slug: 'style', version: '', content: '' }] },
        'dev',
        'alice'
      )
    );
  });

  it('adds exactly one block at this level', async () => {
    overlaysFor({});
    mockApi.listModules.mockResolvedValue({
      success: true,
      modules: [
        { slug: 'rules', kind: 'instruction', version: '1.0.0', sha256: 'abcdef0123456789' },
        { slug: 'style', kind: 'document', version: '2.0.0', sha256: 'bbbbbbbbbbbbbbbb' },
      ],
    });
    await openComposer();

    fireEvent.change(screen.getByLabelText('Add a block'), { target: { value: 'style' } });
    fireEvent.change(screen.getByLabelText('Block version'), { target: { value: '2.0.0' } });
    fireEvent.click(screen.getByRole('button', { name: 'Add at Seat' }));

    await waitFor(() =>
      expect(mockApi.putOverlay).toHaveBeenCalledWith(
        'seat',
        { ops: [{ kind: 'add', slug: 'style', version: '2.0.0', content: '' }] },
        'dev',
        'alice'
      )
    );
  });

  it('refuses to add a block already in effect at this level', async () => {
    overlaysFor({});
    await openComposer();

    expect(screen.getByRole('option', { name: 'rules (already in effect)' })).toBeDisabled();
    expect(screen.getByRole('button', { name: 'Add at Seat' })).toBeDisabled();
  });

  it('shows why a block cannot be removed at this level rather than doing nothing', async () => {
    overlaysFor({ seat: [{ kind: 'remove', slug: 'rules', version: '', content: '' }] });
    await openComposer();

    const blocks = await screen.findByRole('list', { name: 'Composed blocks' });
    expect(
      within(blocks).getByText('already removed at seat: the resolver refuses a second remove')
    ).toBeInTheDocument();
    expect(within(blocks).getByRole('button', { name: /Restore/ })).toBeInTheDocument();
  });

  // The owner's pin ruling: a pin labels what it does - sets the version in effect at its scope -
  // and must not read as protection; the resolver has no pin lock and a removal below still wins.
  it('labels a pin as what it does and still removes the block - no invented pin lock', async () => {
    overlaysFor({ company: [{ kind: 'pin', slug: 'rules', version: '1.2.0', content: '' }] });
    await openComposer();

    const blocks = await screen.findByRole('list', { name: 'Composed blocks' });
    const badge = within(blocks).getByText('pinned at company');
    expect(badge.textContent).toBe('pinned at company');
    // A padlock glyph claimed a protection the resolver does not enforce.
    expect(badge.querySelector('svg')).toBeNull();
    expect(
      within(blocks).getByText(
        'A pin sets the version in effect at company for this block and does nothing else - it is not a lock, so removing the block still removes it.'
      )
    ).toBeInTheDocument();

    const row = within(blocks).getByText('rules@1.2.0').closest('li') as HTMLElement;
    expect(within(row).getByRole('button', { name: /Remove here/ })).toBeEnabled();
    fireEvent.click(within(row).getByRole('button', { name: /Remove here/ }));

    await waitFor(() =>
      expect(mockApi.putOverlay).toHaveBeenCalledWith(
        'seat',
        { ops: [{ kind: 'remove', slug: 'rules', version: '', content: '' }] },
        'dev',
        'alice'
      )
    );
  });
});

describe('SeatAuthoringPage mcp blocks', () => {
  const mcpModules = [
    { slug: 'rules', kind: 'instruction' as const, version: '1.0.0', sha256: 'abcdef0123456789' },
    { slug: 'agenthub-http', kind: 'mcp' as const, version: '1.0.0', sha256: '1111111111111111' },
    { slug: 'sequential-thinking', kind: 'mcp' as const, version: '1.0.0', sha256: '2222222222222222' },
  ];

  const overlaysFor = (ops: Partial<Record<SeatOverlayScope, SeatOverlayOp[]>>) => {
    mockApi.getOverlay.mockImplementation(async (scope) => ({
      success: true,
      overlay: { scope, ops: ops[scope] ?? [] },
    }));
  };

  it('names an mcp entry by its server and transport, not by its tools', async () => {
    mockApi.listModules.mockResolvedValue({ success: true, modules: mcpModules });
    renderPage();

    expect(await screen.findByRole('option', { name: 'agenthub-http — agenthub_http · http' })).toBeInTheDocument();
    expect(
      await screen.findByRole('option', { name: 'sequential-thinking — sequential-thinking · stdio' })
    ).toBeInTheDocument();
  });

  it('renders two mcp rows with their inheritance labels, and removing one writes the level outcome', async () => {
    mockApi.listModules.mockResolvedValue({ success: true, modules: mcpModules });
    overlaysFor({
      company: [{ kind: 'add', slug: 'agenthub-http', version: '1.0.0', content: '' }],
      room: [{ kind: 'add', slug: 'sequential-thinking', version: '1.0.0', content: '' }],
    });
    renderPage();

    const blocks = await screen.findByRole('list', { name: 'Composed blocks' });
    await within(blocks).findByText('agenthub_http · http');
    await within(blocks).findByText('sequential-thinking · stdio');

    const httpRow = within(blocks).getByText('agenthub-http@1.0.0').closest('li') as HTMLElement;
    expect(within(httpRow).getByText('inherited from company')).toBeInTheDocument();
    expect(
      within(httpRow).getByText('Removing here: removed at seat · still defined at company')
    ).toBeInTheDocument();

    const stdioRow = within(blocks).getByText('sequential-thinking@1.0.0').closest('li') as HTMLElement;
    expect(within(stdioRow).getByText('inherited from room')).toBeInTheDocument();
    expect(within(stdioRow).getByRole('button', { name: /Remove here/ })).toBeEnabled();

    fireEvent.click(within(httpRow).getByRole('button', { name: /Remove here/ }));

    await waitFor(() =>
      expect(mockApi.putOverlay).toHaveBeenCalledWith(
        'seat',
        { ops: [{ kind: 'remove', slug: 'agenthub-http', version: '', content: '' }] },
        'dev',
        'alice'
      )
    );
  });

  it('offers mcp in the module kind union the publish path uses', async () => {
    renderPage();

    fireEvent.change(await screen.findByLabelText('Module kind'), { target: { value: 'mcp' } });

    expect(screen.getByLabelText('Module kind')).toHaveValue('mcp');
  });
});
