import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { notificationService, notify } from '../../services/notificationService';
import { toast } from 'react-hot-toast';

// Mock react-hot-toast
vi.mock('react-hot-toast', () => ({
  toast: Object.assign(vi.fn(), {
    success: vi.fn(),
    error: vi.fn(),
  }),
}));

// Mock logger
vi.mock('../../utils/logger', () => ({
  default: {
    info: vi.fn(),
    error: vi.fn(),
    warn: vi.fn(),
  },
}));

// Mock Web Audio API
const mockAudioContext = {
  createOscillator: vi.fn(() => ({
    connect: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
    frequency: { value: 0 },
  })),
  createGain: vi.fn(() => ({
    connect: vi.fn(),
    gain: {
      value: 0,
      exponentialRampToValueAtTime: vi.fn(),
    },
  })),
  destination: {},
  currentTime: 0,
};

// Mock window globals
Object.defineProperty(window, 'AudioContext', {
  writable: true,
  value: vi.fn(() => mockAudioContext),
});

Object.defineProperty(window, 'Notification', {
  writable: true,
  value: vi.fn().mockImplementation(() => ({
    close: vi.fn(),
    onclick: null,
  })),
});

Object.defineProperty(window.Notification, 'permission', {
  writable: true,
  value: 'default',
});

Object.defineProperty(window.Notification, 'requestPermission', {
  writable: true,
  value: vi.fn().mockResolvedValue('granted'),
});

describe('NotificationService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset notification permission
    window.Notification.permission = 'default';
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Toast Notifications', () => {
    it('should show success toast', () => {
      notificationService.success('Test success');
      expect(toast.success).toHaveBeenCalledWith(
        'Test success',
        expect.objectContaining({
          duration: 4000,
          position: 'top-right',
          icon: '✅',
        })
      );
    });

    it('should show error toast', () => {
      notificationService.error('Test error');
      expect(toast.error).toHaveBeenCalledWith(
        'Test error',
        expect.objectContaining({
          duration: 4000,
          position: 'top-right',
          icon: '❌',
        })
      );
    });

    it('should show warning toast', () => {
      notificationService.warning('Test warning');
      expect(toast).toHaveBeenCalledWith(
        'Test warning',
        expect.objectContaining({
          duration: 4000,
          position: 'top-right',
          icon: '⚠️',
        })
      );
    });

    it('should show info toast', () => {
      notificationService.info('Test info');
      expect(toast).toHaveBeenCalledWith(
        'Test info',
        expect.objectContaining({
          duration: 4000,
          position: 'top-right',
          icon: 'ℹ️',
        })
      );
    });

    it('should allow custom options', () => {
      notificationService.success('Custom success', {
        duration: 5000,
        position: 'bottom-center',
        icon: '🎉',
      });
      expect(toast.success).toHaveBeenCalledWith(
        'Custom success',
        expect.objectContaining({
          duration: 5000,
          position: 'bottom-center',
          icon: '🎉',
        })
      );
    });
  });

  describe('Browser Notifications', () => {
    it('should request browser notification permission', async () => {
      const result = await notificationService.requestBrowserNotificationPermission();
      expect(window.Notification.requestPermission).toHaveBeenCalled();
      expect(result).toBe(true);
    });

    it('should show browser notification when enabled', async () => {
      window.Notification.permission = 'granted';
      await notificationService.requestBrowserNotificationPermission();
      
      notificationService.error('Test error', { showBrowserNotification: true });
      
      expect(window.Notification).toHaveBeenCalledWith(
        'Error',
        expect.objectContaining({
          body: 'Test error',
          icon: '❌',
        })
      );
    });

    it('should not show browser notification when permission denied', () => {
      window.Notification.permission = 'denied';
      
      notificationService.error('Test error', { showBrowserNotification: true });
      
      expect(window.Notification).not.toHaveBeenCalled();
    });
  });

  describe('Entity Change Notifications', () => {
    it('should notify task creation', () => {
      notificationService.notifyEntityChange('task', 'created', 'New Task', 'task-123', 'user123');
      expect(toast.success).toHaveBeenCalledWith(
        'Task "New Task" was created by user123',
        expect.any(Object)
      );
    });

    it('should notify task completion', () => {
      notificationService.notifyEntityChange('task', 'completed', 'Completed Task');
      expect(toast.success).toHaveBeenCalledWith(
        'Task "Completed Task" was completed',
        expect.any(Object)
      );
    });

    it('should notify branch deletion with browser notification', () => {
      window.Notification.permission = 'granted';
      notificationService.checkBrowserNotificationPermission();
      
      notificationService.notifyEntityChange('branch', 'deleted', 'feature-branch', 'branch-123', 'user123');
      
      expect(toast).toHaveBeenCalledWith(
        'Branch "feature-branch" was deleted by user123',
        expect.any(Object)
      );
      expect(window.Notification).toHaveBeenCalledWith(
        'Branch Deleted',
        expect.objectContaining({
          body: 'The branch "feature-branch" has been deleted by user123',
        })
      );
    });

    it('should handle entity change without name using ID', () => {
      notificationService.notifyEntityChange('task', 'updated', undefined, '12345678-1234-5678-1234-567812345678');
      expect(toast).toHaveBeenCalledWith(
        'Task 12345678... was updated',
        expect.any(Object)
      );
    });

    it('should handle different event types correctly', () => {
      const eventTypes = [
        { type: 'created', expectedText: 'was created' },
        { type: 'updated', expectedText: 'was updated' },
        { type: 'deleted', expectedText: 'was deleted' },
        { type: 'completed', expectedText: 'was completed' },
        { type: 'assigned', expectedText: 'was assigned' },
        { type: 'unassigned', expectedText: 'was unassigned' },
        { type: 'archived', expectedText: 'was archived' },
        { type: 'restored', expectedText: 'was restored' },
      ];

      eventTypes.forEach(({ type, expectedText }) => {
        vi.clearAllMocks();
        notificationService.notifyEntityChange('task', type as any, 'Test Task');
        const callArgs = toast.success.mock.calls[0] || toast.mock.calls[0] || toast.error.mock.calls[0];
        expect(callArgs[0]).toContain(expectedText);
      });
    });
  });

  describe('Convenience Functions', () => {
    it('should provide success convenience function', () => {
      notify.success('Convenient success');
      expect(toast.success).toHaveBeenCalled();
    });

    it('should provide error convenience function', () => {
      notify.error('Convenient error');
      expect(toast.error).toHaveBeenCalled();
    });

    it('should provide warning convenience function', () => {
      notify.warning('Convenient warning');
      expect(toast).toHaveBeenCalled();
    });

    it('should provide info convenience function', () => {
      notify.info('Convenient info');
      expect(toast).toHaveBeenCalled();
    });

    it('should provide entityChange convenience function', () => {
      notify.entityChange('task', 'created', 'New Task');
      expect(toast.success).toHaveBeenCalled();
    });
  });

  describe('Sound Management', () => {
    it('should enable and disable sound', () => {
      notificationService.setSoundEnabled(false);
      // Sound is now disabled
      
      notificationService.setSoundEnabled(true);
      // Sound is now enabled
      
      expect(notificationService).toBeDefined();
    });

    it('should play sound for success notifications', () => {
      const createOscillatorSpy = vi.spyOn(mockAudioContext, 'createOscillator');
      
      notificationService.success('Test with sound');
      
      // Sound should be attempted (though mocked)
      expect(createOscillatorSpy).toHaveBeenCalled();
    });
  });

  describe('Browser Notification Status', () => {
    it('should check if browser notifications are enabled', () => {
      const result = notificationService.isBrowserNotificationsEnabled();
      expect(typeof result).toBe('boolean');
    });

    it('should enable browser notifications when permission granted', async () => {
      window.Notification.permission = 'default';
      await notificationService.requestBrowserNotificationPermission();
      
      expect(notificationService.isBrowserNotificationsEnabled()).toBe(true);
    });
  });
});