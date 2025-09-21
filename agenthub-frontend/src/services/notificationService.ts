/**
 * Notification Service for displaying alerts to users
 * Supports both toast notifications and browser notifications
 */

import { toastEventBus } from './toastEventBus';
import logger from '../utils/logger';

export type NotificationType = 'success' | 'error' | 'info' | 'warning';
export type EntityType = 'task' | 'subtask' | 'project' | 'branch' | 'context' | 'agent';
export type EventType = 'created' | 'updated' | 'deleted' | 'completed' | 'assigned' | 'unassigned' | 'archived' | 'restored';

interface NotificationOptions {
  duration?: number;
  position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
  icon?: string;
  showBrowserNotification?: boolean;
}

class NotificationService {
  private browserNotificationsEnabled = false;
  private soundEnabled = true;

  constructor() {
    // Initialize notification sound
    this.initializeSound();

    // Check and request browser notification permission
    this.checkBrowserNotificationPermission();
  }

  /**
   * Initialize notification sound
   */
  private initializeSound() {
    try {
      // Create a simple beep sound using Web Audio API
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.frequency.value = 800; // Frequency in Hz
      gainNode.gain.value = 0.1; // Volume

      // Store audio context for later use
      (this as any).audioContext = audioContext;
    } catch (error) {
      logger.warn('Could not initialize notification sound:', error);
    }
  }

  /**
   * Play notification sound
   */
  private playSound() {
    if (!this.soundEnabled) return;

    try {
      const audioContext = (this as any).audioContext;
      if (audioContext) {
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.frequency.value = 800;
        gainNode.gain.value = 0.05;
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.1);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.1);
      }
    } catch (error) {
      // Silently fail if sound cannot be played
    }
  }

  /**
   * Check and request browser notification permission
   */
  async checkBrowserNotificationPermission() {
    if (!('Notification' in window)) {
      logger.info('This browser does not support desktop notification');
      return;
    }

    if (Notification.permission === 'granted') {
      this.browserNotificationsEnabled = true;
    } else if (Notification.permission !== 'denied') {
      // We'll ask for permission when user performs an action
      // Don't ask immediately on page load
      this.browserNotificationsEnabled = false;
    }
  }

  /**
   * Request browser notification permission
   */
  async requestBrowserNotificationPermission(): Promise<boolean> {
    if (!('Notification' in window)) {
      return false;
    }

    const permission = await Notification.requestPermission();
    this.browserNotificationsEnabled = permission === 'granted';
    return this.browserNotificationsEnabled;
  }

  /**
   * Show browser notification
   */
  private showBrowserNotification(title: string, body: string, icon?: string) {
    if (!this.browserNotificationsEnabled || !('Notification' in window) || Notification.permission !== 'granted') {
      return;
    }

    try {
      const notification = new Notification(title, {
        body,
        icon: icon || '/favicon.ico',
        badge: '/favicon.ico',
        tag: 'agenthub-notification',
        requireInteraction: false,
        silent: false
      } as NotificationOptions & { vibrate?: number[] });

      // Auto close after 5 seconds
      setTimeout(() => notification.close(), 5000);

      // Handle click
      notification.onclick = () => {
        window.focus();
        notification.close();
      };
    } catch (error) {
      logger.error('Failed to show browser notification:', error);
    }
  }

  /**
   * Show toast notification
   */
  private showToast(message: string, type: NotificationType, options?: NotificationOptions) {
    // Use toastEventBus instead of react-hot-toast
    toastEventBus.emit(type, message, {
      duration: options?.duration || 4000,
      persistent: options?.duration === Infinity,
      description: options?.icon ? `${options.icon} ${message}` : undefined
    });

    // Play sound for certain types
    if (type === 'success' || type === 'error' || type === 'warning') {
      this.playSound();
    }
  }

  /**
   * Notify about entity changes
   */
  notifyEntityChange(
    entityType: EntityType,
    eventType: EventType,
    entityName?: string,
    entityId?: string,
    userName?: string
  ) {
    const entity = entityType.charAt(0).toUpperCase() + entityType.slice(1);
    const action = this.getActionText(eventType);
    const by = userName ? ` by ${userName}` : '';

    // Build the message
    let message = `${entity}`;
    if (entityName) {
      message += ` "${entityName}"`;
    } else if (entityId) {
      message += ` ${entityId.substring(0, 8)}...`;
    }
    message += ` ${action}${by}`;

    // Determine notification type
    let notificationType: NotificationType = 'info';
    if (eventType === 'created') notificationType = 'success';
    else if (eventType === 'deleted') notificationType = 'warning';
    else if (eventType === 'completed') notificationType = 'success';
    else if (eventType === 'updated') notificationType = 'info';

    // Show toast
    this.showToast(message, notificationType);

    // Show browser notification for important events
    if (eventType === 'deleted' && entityType === 'branch') {
      this.showBrowserNotification(
        `Branch Deleted`,
        `The branch "${entityName || entityId}" has been deleted${by}`,
        '🗑️'
      );
    } else if (eventType === 'deleted' && entityType === 'project') {
      this.showBrowserNotification(
        `Project Deleted`,
        `The project "${entityName || entityId}" has been deleted${by}`,
        '🗑️'
      );
    } else if (eventType === 'completed' && entityType === 'task') {
      this.showBrowserNotification(
        `Task Completed`,
        `"${entityName || entityId}" has been completed${by}`,
        '✅'
      );
    }
  }

  /**
   * Get human-readable action text
   */
  private getActionText(eventType: EventType): string {
    switch (eventType) {
      case 'created': return 'was created';
      case 'updated': return 'was updated';
      case 'deleted': return 'was deleted';
      case 'completed': return 'was completed';
      case 'assigned': return 'was assigned';
      case 'unassigned': return 'was unassigned';
      case 'archived': return 'was archived';
      case 'restored': return 'was restored';
      default: return 'was modified';
    }
  }

  /**
   * Show success notification
   */
  success(message: string, options?: NotificationOptions) {
    this.showToast(message, 'success', options);
  }

  /**
   * Show error notification
   */
  error(message: string, options?: NotificationOptions) {
    this.showToast(message, 'error', options);
    if (options?.showBrowserNotification) {
      this.showBrowserNotification('Error', message, '❌');
    }
  }

  /**
   * Show warning notification
   */
  warning(message: string, options?: NotificationOptions) {
    this.showToast(message, 'warning', options);
  }

  /**
   * Show info notification
   */
  info(message: string, options?: NotificationOptions) {
    this.showToast(message, 'info', options);
  }

  /**
   * Enable/disable sound
   */
  setSoundEnabled(enabled: boolean) {
    this.soundEnabled = enabled;
  }

  /**
   * Check if browser notifications are enabled
   */
  isBrowserNotificationsEnabled(): boolean {
    return this.browserNotificationsEnabled;
  }
}

// Export singleton instance
export const notificationService = new NotificationService();

// Export convenience functions
export const notify = {
  success: (message: string, options?: NotificationOptions) =>
    notificationService.success(message, options),
  error: (message: string, options?: NotificationOptions) =>
    notificationService.error(message, options),
  warning: (message: string, options?: NotificationOptions) =>
    notificationService.warning(message, options),
  info: (message: string, options?: NotificationOptions) =>
    notificationService.info(message, options),
  entityChange: (
    entityType: EntityType,
    eventType: EventType,
    entityName?: string,
    entityId?: string,
    userName?: string
  ) => notificationService.notifyEntityChange(entityType, eventType, entityName, entityId, userName)
};