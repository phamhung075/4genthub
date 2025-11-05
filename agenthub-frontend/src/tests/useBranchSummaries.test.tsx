/**
 * Tests for useBranchSummaries hook (React Query version)
 */

import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useBranchSummaries } from '../hooks/useBranchSummaries';
import { branchService } from '../services/branchService';
import { createTestQueryClient } from './query-utils';

// Mock the branch service
vi.mock('../services/branchService', () => ({
  branchService: {
    loadProjectSummaries: vi.fn(),
    loadUserSummaries: vi.fn(),
  },
}));

describe('useBranchSummaries (React Query)', () => {
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

  it('should load all user summaries by default', async () => {
    const mockData = {
      branches: [
        { id: 'branch-1', name: 'Feature Branch 1', task_count: 5 },
        { id: 'branch-2', name: 'Feature Branch 2', task_count: 3 },
      ],
      projects: [{ id: 'proj-1', name: 'Project 1' }],
    };

    vi.mocked(branchService.loadUserSummaries).mockResolvedValue(mockData);

    const { result } = renderHook(() => useBranchSummaries(), { wrapper });

    expect(result.current.loading).toBe(true);

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.summaries).toEqual(mockData.branches);
    expect(result.current.projects).toEqual(mockData.projects);
    expect(result.current.error).toBeNull();
  });

  it('should load specific project summaries when projectIds provided', async () => {
    const mockBranches = [
      { id: 'branch-1', name: 'Feature Branch 1', task_count: 5 },
    ];

    vi.mocked(branchService.loadProjectSummaries).mockResolvedValue(mockBranches);

    const { result } = renderHook(
      () => useBranchSummaries({ projectIds: ['proj-1'] }),
      { wrapper }
    );

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(branchService.loadProjectSummaries).toHaveBeenCalledWith(['proj-1']);
    expect(result.current.summaries).toEqual(mockBranches);
  });

  it('should handle errors gracefully', async () => {
    vi.mocked(branchService.loadUserSummaries).mockRejectedValue(
      new Error('Failed to load summaries')
    );

    const { result } = renderHook(() => useBranchSummaries(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(result.current.error).toBe('Failed to load summaries');
    expect(result.current.summaries).toEqual([]);
  });

  it('should use React Query cache for subsequent requests', async () => {
    const mockData = {
      branches: [{ id: 'branch-1', name: 'Branch 1', task_count: 1 }],
      projects: [],
    };

    vi.mocked(branchService.loadUserSummaries).mockResolvedValue(mockData);

    const { result, rerender } = renderHook(() => useBranchSummaries(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    expect(branchService.loadUserSummaries).toHaveBeenCalledTimes(1);

    // Rerender - should use cache, not call API again
    rerender();

    expect(branchService.loadUserSummaries).toHaveBeenCalledTimes(1);
  });
});
