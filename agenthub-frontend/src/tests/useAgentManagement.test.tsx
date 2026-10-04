/**
 * Tests for useAgentManagement hooks (React Query version with mutations)
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useUserAgentInstances, useAgentTemplates } from '../hooks/useAgentManagement';
import { agentManagementApiV2 } from '../services/apiV2';
import { createTestQueryClient } from './query-utils';

// Mock the API service
vi.mock('../services/apiV2', () => ({
  agentManagementApiV2: {
    listTemplates: vi.fn(),
    listUserInstances: vi.fn(),
    getUserInstance: vi.fn(),
    createInstance: vi.fn(),
    updateInstance: vi.fn(),
    deleteInstance: vi.fn(),
  },
}));

describe('useAgentTemplates (React Query)', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  it('should load agent templates successfully', async () => {
    const mockTemplates = [
      { id: 'template-1', slug: 'coding-agent', name: 'Coding Agent' },
      { id: 'template-2', slug: 'test-agent', name: 'Test Agent' },
    ];

    vi.mocked(agentManagementApiV2.listTemplates).mockResolvedValue({
      success: true,
      templates: mockTemplates,
    });

    const { result } = renderHook(() => useAgentTemplates(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.templates).toEqual(mockTemplates);
    expect(result.current.error).toBeNull();
  });

  it('should find template by slug', async () => {
    const mockTemplates = [
      { id: 'template-1', slug: 'coding-agent', name: 'Coding Agent' },
    ];

    vi.mocked(agentManagementApiV2.listTemplates).mockResolvedValue({
      success: true,
      templates: mockTemplates,
    });

    const { result } = renderHook(() => useAgentTemplates(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    const template = result.current.getTemplateBySlug('coding-agent');
    expect(template).toEqual(mockTemplates[0]);
  });
});

describe('useUserAgentInstances (React Query with Mutations)', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = createTestQueryClient();
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );

  const mockInstances = [
    {
      id: 'instance-1',
      agent_name: 'My Coding Agent',
      template_id: 'template-1',
      is_enabled: true,
    },
    {
      id: 'instance-2',
      agent_name: 'My Test Agent',
      template_id: 'template-2',
      is_enabled: false,
    },
  ];

  // The mutations write the cache and then invalidate it, which refetches the list. A fake
  // server keeps the list endpoint consistent with what the mutations did.
  let serverInstances: typeof mockInstances;

  const serveInstances = () => {
    serverInstances = [...mockInstances];
    vi.mocked(agentManagementApiV2.listUserInstances).mockImplementation(async () => ({
      success: true,
      instances: [...serverInstances],
    }));
  };

  it('should load user agent instances', async () => {
    vi.mocked(agentManagementApiV2.listUserInstances).mockResolvedValue({
      success: true,
      instances: mockInstances,
    });

    const { result } = renderHook(() => useUserAgentInstances(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.instances).toEqual(mockInstances);
    expect(result.current.error).toBeNull();
  });

  it('should create new agent instance using mutation', async () => {
    serveInstances();

    const newInstance = {
      id: 'instance-3',
      agent_name: 'New Agent',
      template_id: 'template-3',
      is_enabled: true,
    };

    vi.mocked(agentManagementApiV2.createInstance).mockImplementation(async () => {
      serverInstances.push(newInstance);
      return newInstance;
    });

    const { result } = renderHook(() => useUserAgentInstances(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.instances).toHaveLength(2);

    // Create new instance
    await result.current.createInstance({
      agent_name: 'New Agent',
      template_id: 'template-3',
    });

    await waitFor(() => {
      expect(result.current.instances).toHaveLength(3);
      expect(result.current.instances[2]).toEqual(newInstance);
    });
  });

  it('should update agent instance using mutation', async () => {
    serveInstances();

    const updatedInstance = {
      ...mockInstances[0],
      agent_name: 'Updated Agent Name',
    };

    vi.mocked(agentManagementApiV2.updateInstance).mockImplementation(async () => {
      serverInstances[0] = updatedInstance;
      return updatedInstance;
    });

    const { result } = renderHook(() => useUserAgentInstances(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Update instance
    await result.current.updateInstance('instance-1', {
      agent_name: 'Updated Agent Name',
    });

    await waitFor(() => {
      const updated = result.current.instances.find(i => i.id === 'instance-1');
      expect(updated?.agent_name).toBe('Updated Agent Name');
    });
  });

  it('should delete agent instance using mutation', async () => {
    serveInstances();

    vi.mocked(agentManagementApiV2.deleteInstance).mockImplementation(async () => {
      serverInstances = serverInstances.filter(i => i.id !== 'instance-1');
      return { success: true };
    });

    const { result } = renderHook(() => useUserAgentInstances(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.instances).toHaveLength(2);

    // Delete instance
    const deleted = await result.current.deleteInstance('instance-1');

    expect(deleted).toBe(true);

    await waitFor(() => {
      expect(result.current.instances).toHaveLength(1);
      expect(result.current.instances[0].id).toBe('instance-2');
    });
  });

  it('should toggle agent enabled status', async () => {
    serveInstances();

    const toggledInstance = {
      ...mockInstances[1],
      is_enabled: true,
    };

    vi.mocked(agentManagementApiV2.updateInstance).mockImplementation(async () => {
      serverInstances[1] = toggledInstance;
      return toggledInstance;
    });

    const { result } = renderHook(() => useUserAgentInstances(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.instances[1].is_enabled).toBe(false);

    // Toggle enabled
    await result.current.toggleEnabled('instance-2', true);

    await waitFor(() => {
      const updated = result.current.instances.find(i => i.id === 'instance-2');
      expect(updated?.is_enabled).toBe(true);
    });
  });

  it('should show loading state during mutations', async () => {
    vi.mocked(agentManagementApiV2.listUserInstances).mockResolvedValue({
      success: true,
      instances: mockInstances,
    });

    const newInstance = {
      id: 'instance-3',
      agent_name: 'New Agent',
      template_id: 'template-3',
      is_enabled: true,
    };

    let resolveCreate: (value: any) => void;
    const createPromise = new Promise(resolve => {
      resolveCreate = resolve;
    });

    vi.mocked(agentManagementApiV2.createInstance).mockReturnValue(createPromise);

    const { result } = renderHook(() => useUserAgentInstances(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Start mutation
    result.current.createInstance({
      agent_name: 'New Agent',
      template_id: 'template-3',
    });

    // Should show loading
    await waitFor(() => {
      expect(result.current.isLoading).toBe(true);
    });

    // Resolve mutation
    resolveCreate!(newInstance);

    // Loading should complete
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it('should refetch the list after a mutation (cache invalidation)', async () => {
    serveInstances();

    const newInstance = {
      id: 'instance-3',
      agent_name: 'New Agent',
      template_id: 'template-3',
      is_enabled: true,
    };

    vi.mocked(agentManagementApiV2.createInstance).mockImplementation(async () => {
      serverInstances.push(newInstance);
      return newInstance;
    });

    const { result } = renderHook(() => useUserAgentInstances(), { wrapper });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    const initialCount = vi.mocked(agentManagementApiV2.listUserInstances).mock.calls.length;

    // Create mutation
    await result.current.createInstance({
      agent_name: 'New Agent',
      template_id: 'template-3',
    });

    await waitFor(() => {
      expect(result.current.instances).toHaveLength(3);
    });

    // onSuccess writes the cache and invalidates the query, which refetches the list
    await waitFor(() => {
      expect(agentManagementApiV2.listUserInstances).toHaveBeenCalledTimes(initialCount + 1);
    });
  });
});
