import { renderHook, act } from '@testing-library/react';
import { vi, describe, it, expect, beforeEach } from 'vitest';
import { useChangeSubscription, useEntityChanges } from '../../hooks/useChangeSubscription';
import { changePoolService, ChangeNotification } from '../../services/changePoolService';

// Mock the changePoolService
vi.mock('../../services/changePoolService', () => ({
  changePoolService: {
    subscribe: vi.fn(() => vi.fn()), // Returns unsubscribe function
    clearAllSubscriptions: vi.fn()
  }
}));

const mockChangePoolService = vi.mocked(changePoolService);

describe('useChangeSubscription Hook', () => {
  const mockRefreshCallback = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockRefreshCallback.mockClear();
  });

  describe('Basic Subscription', () => {
    it('should subscribe to change pool service on mount', () => {
      const unsubscribeMock = vi.fn();
      mockChangePoolService.subscribe.mockReturnValue(unsubscribeMock);

      renderHook(() =>
        useChangeSubscription({
          componentId: 'TestComponent',
          entityTypes: ['task'],
          refreshCallback: mockRefreshCallback
        })
      );

      expect(mockChangePoolService.subscribe).toHaveBeenCalledWith({
        componentId: 'TestComponent',
        entityTypes: ['task'],
        entityIds: undefined,
        projectId: undefined,
        branchId: undefined,
        refreshCallback: expect.any(Function),
        shouldRefresh: undefined
      });
    });

    it('should pass notification data through to refreshCallback', () => {
      let subscribedCallback: ((notification?: ChangeNotification) => void) | null = null;

      mockChangePoolService.subscribe.mockImplementation((subscription) => {
        subscribedCallback = subscription.refreshCallback;
        return vi.fn();
      });

      renderHook(() =>
        useChangeSubscription({
          componentId: 'TestComponent',
          entityTypes: ['task'],
          refreshCallback: mockRefreshCallback
        })
      );

      // Simulate notification from changePoolService
      const testNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-1',
        eventType: 'created',
        userId: 'user-1',
        data: {
          id: 'task-1',
          title: 'Test Task',
          status: 'todo'
        },
        timestamp: new Date().toISOString()
      };

      act(() => {
        subscribedCallback?.(testNotification);
      });

      expect(mockRefreshCallback).toHaveBeenCalledWith(testNotification);
      expect(mockRefreshCallback).toHaveBeenCalledTimes(1);
    });

    it('should handle refresh without notification data', () => {
      let subscribedCallback: ((notification?: ChangeNotification) => void) | null = null;

      mockChangePoolService.subscribe.mockImplementation((subscription) => {
        subscribedCallback = subscription.refreshCallback;
        return vi.fn();
      });

      renderHook(() =>
        useChangeSubscription({
          componentId: 'TestComponent',
          entityTypes: ['task'],
          refreshCallback: mockRefreshCallback
        })
      );

      act(() => {
        subscribedCallback?.(); // Called without notification data
      });

      expect(mockRefreshCallback).toHaveBeenCalledWith(undefined);
    });
  });

  describe('Subscription Options', () => {
    it('should pass filtering options to changePoolService', () => {
      renderHook(() =>
        useChangeSubscription({
          componentId: 'FilteredComponent',
          entityTypes: ['task', 'subtask'],
          entityIds: ['task-1', 'task-2'],
          projectId: 'project-123',
          branchId: 'branch-456',
          refreshCallback: mockRefreshCallback
        })
      );

      expect(mockChangePoolService.subscribe).toHaveBeenCalledWith({
        componentId: 'FilteredComponent',
        entityTypes: ['task', 'subtask'],
        entityIds: ['task-1', 'task-2'],
        projectId: 'project-123',
        branchId: 'branch-456',
        refreshCallback: expect.any(Function),
        shouldRefresh: undefined
      });
    });

    it('should respect enabled option', () => {
      const { rerender } = renderHook(
        ({ enabled }) =>
          useChangeSubscription({
            componentId: 'ConditionalComponent',
            entityTypes: ['task'],
            refreshCallback: mockRefreshCallback,
            enabled
          }),
        { initialProps: { enabled: false } }
      );

      // Should not subscribe when disabled
      expect(mockChangePoolService.subscribe).not.toHaveBeenCalled();

      // Should subscribe when enabled
      rerender({ enabled: true });
      expect(mockChangePoolService.subscribe).toHaveBeenCalledTimes(1);
    });
  });

  describe('Cleanup', () => {
    it('should unsubscribe on unmount', () => {
      const unsubscribeMock = vi.fn();
      mockChangePoolService.subscribe.mockReturnValue(unsubscribeMock);

      const { unmount } = renderHook(() =>
        useChangeSubscription({
          componentId: 'TestComponent',
          entityTypes: ['task'],
          refreshCallback: mockRefreshCallback
        })
      );

      unmount();

      expect(unsubscribeMock).toHaveBeenCalled();
    });

    it('should resubscribe when dependencies change', () => {
      const unsubscribe1 = vi.fn();
      const unsubscribe2 = vi.fn();
      mockChangePoolService.subscribe
        .mockReturnValueOnce(unsubscribe1)
        .mockReturnValueOnce(unsubscribe2);

      const { rerender } = renderHook(
        ({ branchId }) =>
          useChangeSubscription({
            componentId: 'TestComponent',
            entityTypes: ['task'],
            branchId,
            refreshCallback: mockRefreshCallback
          }),
        { initialProps: { branchId: 'branch-1' } }
      );

      expect(mockChangePoolService.subscribe).toHaveBeenCalledTimes(1);

      // Change branchId - should unsubscribe old and subscribe new
      rerender({ branchId: 'branch-2' });

      expect(unsubscribe1).toHaveBeenCalled();
      expect(mockChangePoolService.subscribe).toHaveBeenCalledTimes(2);
    });
  });
});

describe('useEntityChanges Hook', () => {
  const mockRefreshCallback = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockRefreshCallback.mockClear();
  });

  describe('Simplified API', () => {
    it('should handle single entity type', () => {
      renderHook(() =>
        useEntityChanges('SimpleComponent', 'task', mockRefreshCallback)
      );

      expect(mockChangePoolService.subscribe).toHaveBeenCalledWith({
        componentId: 'SimpleComponent',
        entityTypes: ['task'],
        refreshCallback: expect.any(Function)
      });
    });

    it('should handle multiple entity types', () => {
      renderHook(() =>
        useEntityChanges(
          'MultiComponent',
          ['task', 'subtask'],
          mockRefreshCallback
        )
      );

      expect(mockChangePoolService.subscribe).toHaveBeenCalledWith({
        componentId: 'MultiComponent',
        entityTypes: ['task', 'subtask'],
        refreshCallback: expect.any(Function)
      });
    });

    it('should pass options through', () => {
      renderHook(() =>
        useEntityChanges(
          'OptionsComponent',
          ['task'],
          mockRefreshCallback,
          {
            projectId: 'proj-123',
            branchId: 'branch-456',
            enabled: true // Set to true so subscription actually happens
          }
        )
      );

      expect(mockChangePoolService.subscribe).toHaveBeenCalledWith({
        componentId: 'OptionsComponent',
        entityTypes: ['task'],
        refreshCallback: expect.any(Function),
        projectId: 'proj-123',
        branchId: 'branch-456',
        entityIds: undefined,
        shouldRefresh: undefined
      });
    });

    it('should pass notification data to callback', () => {
      let subscribedCallback: ((notification?: ChangeNotification) => void) | null = null;

      mockChangePoolService.subscribe.mockImplementation((subscription) => {
        subscribedCallback = subscription.refreshCallback;
        return vi.fn();
      });

      renderHook(() =>
        useEntityChanges('DataComponent', ['task'], mockRefreshCallback)
      );

      const notification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-1',
        eventType: 'updated',
        userId: 'user-1',
        data: { id: 'task-1', title: 'Updated Task' },
        timestamp: new Date().toISOString()
      };

      act(() => {
        subscribedCallback?.(notification);
      });

      expect(mockRefreshCallback).toHaveBeenCalledWith(notification);
    });
  });
});