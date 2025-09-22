/**
 * Notification Service for displaying alerts to users
 * Supports both toast notifications and browser notifications
 */

import { toastEventBus } from './toastEventBus';
import logger from '../utils/logger';

export type NotificationType = 'success' | 'error' | 'info' | 'warning';
export type EntityType = 'task' | 'subtask' | 'project' | 'branch' | 'context' | 'agent';
export type EventType = 'created' | 'updated' | 'deleted' | 'completed' | 'assigned' | 'unassigned' | 'archived' | 'restored';

interface WSMessage {
  id: string;
  version: '2.0';
  type: 'update' | 'bulk' | 'sync' | 'heartbeat' | 'error';
  timestamp: string;
  sequence: number;
  payload: {
    entity: string;
    action: string;
    data: {
      primary: any | any[];
      cascade?: any;
    };
  };
  metadata: {
    source: 'mcp-ai' | 'user' | 'system';
    userId?: string;
    sessionId?: string;
    correlationId?: string;
    batchId?: string;
  };
}

interface NotificationOptions {
  duration?: number;
  position?: 'top-left' | 'top-center' | 'top-right' | 'bottom-left' | 'bottom-center' | 'bottom-right';
  icon?: string;
  showBrowserNotification?: boolean;
}

class NotificationService {
  private browserNotificationsEnabled = false;
  private soundEnabled = true;
  private recentNotifications = new Map<string, number>();
  private webSocketInitialized = false;

  constructor() {
    // Initialize notification sound
    this.initializeSound();

    // Check and request browser notification permission
    this.checkBrowserNotificationPermission();

    // Clean up old notifications every 30 seconds
    setInterval(() => this.cleanupOldNotifications(), 30000);
  }

  /**
   * Clean up old notification entries (older than 10 seconds)
   */
  private cleanupOldNotifications() {
    const now = Date.now();
    const cutoff = 10000; // 10 seconds

    for (const [key, timestamp] of this.recentNotifications.entries()) {
      if (now - timestamp > cutoff) {
        this.recentNotifications.delete(key);
      }
    }
  }

  /**
   * Check if notification is a duplicate within the deduplication window
   */
  private isDuplicate(entityType: EntityType, eventType: EventType, entityId?: string): boolean {
    const key = `${entityType}:${eventType}:${entityId || 'unknown'}`;
    const now = Date.now();
    const lastNotification = this.recentNotifications.get(key);

    // 5-second deduplication window
    if (lastNotification && (now - lastNotification) < 5000) {
      logger.debug(`Notification deduplication: Skipping duplicate ${key}`);
      return true;
    }

    this.recentNotifications.set(key, now);
    return false;
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
    // Use toastEventBus convenience methods to ensure deduplication
    const description = options?.icon ? `${options.icon} ${message}` : options?.duration ? undefined : undefined;

    switch (type) {
      case 'success':
        toastEventBus.success(message, description);
        break;
      case 'error':
        toastEventBus.error(message, description);
        break;
      case 'warning':
        toastEventBus.warning(message, description);
        break;
      case 'info':
        toastEventBus.info(message, description);
        break;
    }

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
    // Check for duplicate notifications
    if (this.isDuplicate(entityType, eventType, entityId)) {
      logger.debug('Skipping duplicate notification:', { entityType, eventType, entityId, entityName });
      return;
    }

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

  /**
   * Initialize WebSocket notification integration
   */
  initializeWebSocketListener(webSocketClient: any): () => void {
    if (this.webSocketInitialized) {
      logger.warn('🔔 NotificationService: WebSocket already initialized');
      return () => {};
    }

    logger.info('🔔 NotificationService: Initializing WebSocket notification integration...');

    // Subscribe to WebSocket update messages
    const unsubscribe = webSocketClient.on('update', (message: WSMessage) => {
      this.handleWebSocketMessage(message);
    });

    this.webSocketInitialized = true;
    logger.info('🔔 NotificationService: WebSocket integration initialized successfully');

    // Return cleanup function
    return () => {
      logger.debug('🔔 NotificationService: Cleaning up WebSocket integration');

      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }

      this.webSocketInitialized = false;
    };
  }

  /**
   * Handle incoming WebSocket messages and trigger appropriate notifications
   */
  private handleWebSocketMessage(message: WSMessage): void {
    // Only process update messages from user actions (not AI batched updates)
    if (message.type !== 'update' || message.metadata?.source === 'mcp-ai') {
      return;
    }

    const { entity, action } = message.payload;
    const data = message.payload.data.primary;

    logger.debug('🔔 NotificationService: Processing WebSocket message:', {
      entity,
      action,
      source: message.metadata?.source,
      messageId: message.id
    });

    // Map WebSocket actions to notification event types
    const eventType = this.mapActionToEventType(action);
    if (!eventType) {
      logger.debug('🔔 NotificationService: Ignoring unmapped action:', action);
      return;
    }

    // Extract entity information
    const entityName = this.extractEntityName(data, entity);
    const entityId = this.extractEntityId(data);
    const userName = this.extractUserName(message.metadata);

    // Trigger notification (with deduplication built-in)
    try {
      this.notifyEntityChange(
        entity as EntityType,
        eventType,
        entityName,
        entityId,
        userName
      );

      logger.debug(`✅ NotificationService: Triggered ${eventType} notification for ${entity}`);
    } catch (error) {
      logger.error('❌ NotificationService: Failed to trigger notification:', error);
    }
  }

  /**
   * Map WebSocket action to notification event type
   */
  private mapActionToEventType(action: string): EventType | null {
    const actionMap: Record<string, EventType> = {
      'create': 'created',
      'created': 'created',
      'update': 'updated',
      'updated': 'updated',
      'delete': 'deleted',
      'deleted': 'deleted',
      'complete': 'completed',
      'completed': 'completed',
      'assign': 'assigned',
      'assigned': 'assigned',
      'unassign': 'unassigned',
      'unassigned': 'unassigned',
      'archive': 'archived',
      'archived': 'archived',
      'restore': 'restored',
      'restored': 'restored'
    };

    return actionMap[action.toLowerCase()] || null;
  }

  /**
   * Extract entity name from WebSocket data
   */
  private extractEntityName(data: any, entityType: string): string | undefined {
    if (!data) return undefined;

    // Try various common name fields
    const nameFields = ['name', 'title', 'displayName', 'label'];

    for (const field of nameFields) {
      if (data[field] && typeof data[field] === 'string') {
        return data[field];
      }
    }

    // Entity-specific name extraction
    if (entityType === 'task' || entityType === 'subtask') {
      return data.title || data.name;
    } else if (entityType === 'project') {
      return data.name || data.title;
    } else if (entityType === 'branch') {
      return data.git_branch_name || data.name;
    }

    return undefined;
  }

  /**
   * Extract entity ID from WebSocket data
   */
  private extractEntityId(data: any): string | undefined {
    if (!data) return undefined;
    return data.id || data.uuid || data.entityId;
  }

  /**
   * Extract user name from WebSocket metadata
   */
  private extractUserName(metadata: any): string | undefined {
    if (!metadata) return undefined;
    return metadata.userName || metadata.userDisplayName || metadata.userId;
  }

  /**
   * Check if WebSocket integration is initialized
   */
  isWebSocketInitialized(): boolean {
    return this.webSocketInitialized;
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