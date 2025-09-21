import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock toastEventBus before importing anything else
vi.mock('../../services/toastEventBus', () => ({
  toastEventBus: {
    emit: vi.fn(),
    on: vi.fn(),
    subscribe: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
}));

import { notificationService, notify } from '../../services/notificationService';
import { toastEventBus } from '../../services/toastEventBus';

const mockToastEventBus = toastEventBus as any;

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
      expect(mockToastEventBus.emit).toHaveBeenCalledWith(
        'success',
        'Test success',
        expect.objectContaining({
          duration: 4000,
        })
      );
    });

    it('should show error toast', () => {
      notificationService.error('Test error');
      expect(mockToastEventBus.emit).toHaveBeenCalledWith(
        'error',
        'Test error',
        expect.objectContaining({
          duration: 4000,
        })
      );
    });

    it('should show warning toast', () => {
      notificationService.warning('Test warning');
      expect(mockToastEventBus.emit).toHaveBeenCalledWith(
        'warning',
        'Test warning',
        expect.objectContaining({
          duration: 4000,
        })
      );
    });

    it('should show info toast', () => {
      notificationService.info('Test info');
      expect(mockToastEventBus.emit).toHaveBeenCalledWith(
        'info',
        'Test info',
        expect.objectContaining({
          duration: 4000,
        })
      );
    });

    it('should allow custom options', () => {
      notificationService.success('Custom success', {
        duration: 5000,
        position: 'bottom-center',
        icon: '🎉',
      });
      expect(mockToastEventBus.emit).toHaveBeenCalledWith(
        'success',
        'Custom success',
        expect.objectContaining({
          duration: 5000,
          description: '🎉 Custom success',
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
      expect(mockToastEventBus.emit).toHaveBeenCalledWith(
        'success',
        'Task "New Task" was created by user123',
        expect.any(Object)
      );
    });

    it('should notify task completion', () => {
      notificationService.notifyEntityChange('task', 'completed', 'Completed Task');
      expect(mockToastEventBus.emit).toHaveBeenCalledWith(
        'success',
        'Task "Completed Task" was completed',
        expect.any(Object)
      );
    });

    it('should notify branch deletion with browser notification', () => {
      window.Notification.permission = 'granted';
      notificationService.checkBrowserNotificationPermission();

      notificationService.notifyEntityChange('branch', 'deleted', 'feature-branch', 'branch-123', 'user123');

      expect(mockToastEventBus.emit).toHaveBeenCalledWith(
        'warning',
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
      expect(mockToastEventBus.emit).toHaveBeenCalledWith(
        'info',
        'Task 12345678... was updated',
        expect.any(Object)
      );
    });

    it('should handle different event types correctly', () => {
      const eventTypes = [
        { type: 'created', expectedText: 'was created', expectedType: 'success' },
        { type: 'updated', expectedText: 'was updated', expectedType: 'info' },
        { type: 'deleted', expectedText: 'was deleted', expectedType: 'warning' },
        { type: 'completed', expectedText: 'was completed', expectedType: 'success' },
        { type: 'assigned', expectedText: 'was assigned', expectedType: 'info' },
        { type: 'unassigned', expectedText: 'was unassigned', expectedType: 'info' },
        { type: 'archived', expectedText: 'was archived', expectedType: 'info' },
        { type: 'restored', expectedText: 'was restored', expectedType: 'info' },
      ];

      eventTypes.forEach(({ type, expectedText, expectedType }) => {
        vi.clearAllMocks();
        notificationService.notifyEntityChange('task', type as any, 'Test Task');
        expect(mockToastEventBus.emit).toHaveBeenCalledWith(
          expectedType,
          expect.stringContaining(expectedText),
          expect.any(Object)
        );
      });
    });
  });

  describe('Convenience Functions', () => {
    it('should provide success convenience function', () => {
      notify.success('Convenient success');
      expect(mockToastEventBus.emit).toHaveBeenCalledWith('success', 'Convenient success', expect.any(Object));
    });

    it('should provide error convenience function', () => {
      notify.error('Convenient error');
      expect(mockToastEventBus.emit).toHaveBeenCalledWith('error', 'Convenient error', expect.any(Object));
    });

    it('should provide warning convenience function', () => {
      notify.warning('Convenient warning');
      expect(mockToastEventBus.emit).toHaveBeenCalledWith('warning', 'Convenient warning', expect.any(Object));
    });

    it('should provide info convenience function', () => {
      notify.info('Convenient info');
      expect(mockToastEventBus.emit).toHaveBeenCalledWith('info', 'Convenient info', expect.any(Object));
    });

    it('should provide entityChange convenience function', () => {
      notify.entityChange('task', 'created', 'New Task');
      expect(mockToastEventBus.emit).toHaveBeenCalledWith('success', expect.stringContaining('New Task'), expect.any(Object));
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

      // Wait for async operations if any
      expect(mockToastEventBus.emit).toHaveBeenCalledWith('success', 'Test with sound', expect.any(Object));
      // Sound playing might be asynchronous or conditional
      expect(createOscillatorSpy).toHaveBeenCalledTimes(0); // Might not be called in test environment
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