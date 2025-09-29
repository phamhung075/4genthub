import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import { changePoolService, ChangeNotification, ComponentSubscription, EntityType } from '../../services/changePoolService';

describe('ChangePoolService Real-time Updates', () => {
  beforeEach(() => {
    // Clear all subscriptions before each test
    changePoolService.clearAllSubscriptions();
    vi.clearAllMocks();
  });

  afterEach(() => {
    changePoolService.clearAllSubscriptions();
  });

  describe('Subscription Management', () => {
    it('should register component subscriptions correctly', () => {
      const mockCallback = vi.fn();
      const subscription: ComponentSubscription = {
        componentId: 'LazyTaskList-test',
        entityTypes: ['task'],
        branchId: 'branch-123',
        refreshCallback: mockCallback
      };

      const unsubscribe = changePoolService.subscribe(subscription);
      expect(typeof unsubscribe).toBe('function');

      const subscriptions = changePoolService.getSubscriptions();
      expect(subscriptions).toHaveLength(1);
      expect(subscriptions[0].componentId).toBe('LazyTaskList-test');
    });

    it('should filter notifications by branch ID', () => {
      const mockCallback = vi.fn();
      const subscription: ComponentSubscription = {
        componentId: 'LazyTaskList-branch-123',
        entityTypes: ['task'],
        branchId: 'branch-123',
        refreshCallback: mockCallback
      };

      changePoolService.subscribe(subscription);

      // Notification for different branch - should NOT trigger callback
      const wrongBranchNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-1',
        eventType: 'created',
        userId: 'user-1',
        metadata: { git_branch_id: 'branch-456' },
        timestamp: new Date().toISOString()
      };

      changePoolService.processChange(wrongBranchNotification);
      expect(mockCallback).not.toHaveBeenCalled();

      // Notification for correct branch - SHOULD trigger callback
      const correctBranchNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-1',
        eventType: 'created',
        userId: 'user-1',
        metadata: { git_branch_id: 'branch-123' },
        timestamp: new Date().toISOString()
      };

      changePoolService.processChange(correctBranchNotification);
      expect(mockCallback).toHaveBeenCalledWith(correctBranchNotification);
    });

    it('should pass notification data to callback', () => {
      const mockCallback = vi.fn();
      const subscription: ComponentSubscription = {
        componentId: 'LazyTaskList-data-test',
        entityTypes: ['task'],
        refreshCallback: mockCallback
      };

      changePoolService.subscribe(subscription);

      const notificationWithData: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-1',
        eventType: 'created',
        userId: 'user-1',
        data: {
          id: 'task-1',
          title: 'New Task',
          status: 'todo',
          created_at: new Date().toISOString()
        },
        timestamp: new Date().toISOString()
      };

      changePoolService.processChange(notificationWithData);

      expect(mockCallback).toHaveBeenCalledWith(notificationWithData);
      expect(mockCallback).toHaveBeenCalledTimes(1);
    });
  });

  describe('Real-time Task Operations', () => {
    it('should process CREATED task notifications with data', () => {
      const mockCallback = vi.fn();
      changePoolService.subscribe({
        componentId: 'LazyTaskList-create-test',
        entityTypes: ['task'],
        branchId: 'branch-123',
        refreshCallback: mockCallback
      });

      const createNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'new-task-123',
        eventType: 'created',
        userId: 'user-1',
        data: {
          id: 'new-task-123',
          title: 'Newly Created Task',
          status: 'todo',
          priority: 'high',
          assignees: ['agent-1'],
          created_at: new Date().toISOString()
        },
        metadata: {
          git_branch_id: 'branch-123',
          project_id: 'project-123'
        },
        timestamp: new Date().toISOString()
      };

      changePoolService.processChange(createNotification);

      expect(mockCallback).toHaveBeenCalledWith(createNotification);
      expect(mockCallback.mock.calls[0][0].data.title).toBe('Newly Created Task');
    });

    it('should process UPDATED task notifications with data', () => {
      const mockCallback = vi.fn();
      changePoolService.subscribe({
        componentId: 'LazyTaskList-update-test',
        entityTypes: ['task'],
        branchId: 'branch-123',
        refreshCallback: mockCallback
      });

      const updateNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-1',
        eventType: 'updated',
        userId: 'user-1',
        data: {
          id: 'task-1',
          title: 'Updated Task Title',
          status: 'in_progress',
          priority: 'critical'
        },
        metadata: {
          git_branch_id: 'branch-123'
        },
        timestamp: new Date().toISOString()
      };

      changePoolService.processChange(updateNotification);

      expect(mockCallback).toHaveBeenCalledWith(updateNotification);
      expect(mockCallback.mock.calls[0][0].data.status).toBe('in_progress');
    });

    it('should process DELETED task notifications', () => {
      const mockCallback = vi.fn();
      changePoolService.subscribe({
        componentId: 'LazyTaskList-delete-test',
        entityTypes: ['task'],
        branchId: 'branch-123',
        refreshCallback: mockCallback
      });

      const deleteNotification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-to-delete',
        eventType: 'deleted',
        userId: 'user-1',
        metadata: {
          git_branch_id: 'branch-123'
        },
        timestamp: new Date().toISOString()
      };

      changePoolService.processChange(deleteNotification);

      expect(mockCallback).toHaveBeenCalledWith(deleteNotification);
    });
  });

  describe('Multiple Subscribers', () => {
    it('should notify all matching subscribers', () => {
      const callback1 = vi.fn();
      const callback2 = vi.fn();
      const callback3 = vi.fn();

      // Two subscribers for same branch
      changePoolService.subscribe({
        componentId: 'LazyTaskList-1',
        entityTypes: ['task'],
        branchId: 'branch-123',
        refreshCallback: callback1
      });

      changePoolService.subscribe({
        componentId: 'TaskCounter-1',
        entityTypes: ['task'],
        branchId: 'branch-123',
        refreshCallback: callback2
      });

      // One subscriber for different branch
      changePoolService.subscribe({
        componentId: 'LazyTaskList-2',
        entityTypes: ['task'],
        branchId: 'branch-456',
        refreshCallback: callback3
      });

      const notification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-1',
        eventType: 'created',
        userId: 'user-1',
        metadata: { git_branch_id: 'branch-123' },
        timestamp: new Date().toISOString()
      };

      changePoolService.processChange(notification);

      expect(callback1).toHaveBeenCalledWith(notification);
      expect(callback2).toHaveBeenCalledWith(notification);
      expect(callback3).not.toHaveBeenCalled(); // Different branch
    });
  });

  describe('Error Handling', () => {
    it('should handle callback errors gracefully', () => {
      const errorCallback = vi.fn(() => {
        throw new Error('Callback error');
      });
      const successCallback = vi.fn();

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      changePoolService.subscribe({
        componentId: 'ErrorComponent',
        entityTypes: ['task'],
        refreshCallback: errorCallback
      });

      changePoolService.subscribe({
        componentId: 'SuccessComponent',
        entityTypes: ['task'],
        refreshCallback: successCallback
      });

      const notification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-1',
        eventType: 'created',
        userId: 'user-1',
        timestamp: new Date().toISOString()
      };

      // Should not throw despite error in one callback
      expect(() => {
        changePoolService.processChange(notification);
      }).not.toThrow();

      expect(errorCallback).toHaveBeenCalled();
      expect(successCallback).toHaveBeenCalled();
      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });
  });

  describe('Subscription Cleanup', () => {
    it('should unsubscribe correctly', () => {
      const mockCallback = vi.fn();
      const unsubscribe = changePoolService.subscribe({
        componentId: 'TestComponent',
        entityTypes: ['task'],
        refreshCallback: mockCallback
      });

      expect(changePoolService.getSubscriptions()).toHaveLength(1);

      unsubscribe();

      expect(changePoolService.getSubscriptions()).toHaveLength(0);

      // Notification after unsubscribe should not trigger callback
      const notification: ChangeNotification = {
        entityType: 'task',
        entityId: 'task-1',
        eventType: 'created',
        userId: 'user-1',
        timestamp: new Date().toISOString()
      };

      changePoolService.processChange(notification);
      expect(mockCallback).not.toHaveBeenCalled();
    });
  });
});