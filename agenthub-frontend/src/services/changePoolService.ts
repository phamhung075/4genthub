/**
 * Centralized Change Pool Service
 *
 * This service manages which components need to be refreshed when specific
 * notifications are received from the backend. Components register themselves
 * and specify which entities they care about, then get automatically refreshed
 * when those entities change.
 */

import logger from '../utils/logger';

export type EntityType = 'task' | 'subtask' | 'project' | 'branch' | 'context' | 'agent';
export type EventType = 'created' | 'updated' | 'deleted' | 'completed' | 'archived' | 'restored';

export interface ChangeNotification {
  entityType: EntityType;
  entityId: string;
  eventType: EventType;
  userId: string;
  data?: any;
  metadata?: {
    project_id?: string;
    git_branch_id?: string;
    parent_task_id?: string;
    context_level?: string;
    [key: string]: any;
  };
  timestamp: string;
}

export interface ComponentSubscription {
  componentId: string;
  entityTypes: EntityType[];
  entityIds?: string[]; // Specific entity IDs to watch (optional)
  projectId?: string;   // Filter by project
  branchId?: string;    // Filter by branch
  refreshCallback: () => void;
  shouldRefresh?: (notification: ChangeNotification) => boolean; // Custom filter
}

class ChangePoolService {
  private subscriptions: Map<string, ComponentSubscription> = new Map();
  private changeHistory: ChangeNotification[] = [];
  private maxHistorySize = 100;

  /**
   * Register a component to receive updates when entities change
   */
  subscribe(subscription: ComponentSubscription): () => void {
    logger.debug(`📡 ChangePool: Subscribing ${subscription.componentId} to ${subscription.entityTypes.join(', ')}`);

    this.subscriptions.set(subscription.componentId, subscription);

    // Return unsubscribe function
    return () => {
      logger.debug(`📡 ChangePool: Unsubscribing ${subscription.componentId}`);
      this.subscriptions.delete(subscription.componentId);
    };
  }

  /**
   * Process incoming change notification and refresh relevant components
   */
  processChange(notification: ChangeNotification): void {
    logger.debug(`📡 ChangePool: Processing ${notification.entityType} ${notification.eventType} for ${notification.entityId}`);

    // Add to history
    this.changeHistory.unshift(notification);
    if (this.changeHistory.length > this.maxHistorySize) {
      this.changeHistory.pop();
    }

    // Find all components that should be refreshed
    const componentsToRefresh: string[] = [];

    this.subscriptions.forEach((subscription, componentId) => {
      if (this.shouldComponentRefresh(subscription, notification)) {
        componentsToRefresh.push(componentId);

        // Execute the refresh callback
        try {
          subscription.refreshCallback();
          logger.debug(`✅ ChangePool: Refreshed ${componentId} for ${notification.entityType} ${notification.eventType}`);
        } catch (error) {
          logger.error(`❌ ChangePool: Failed to refresh ${componentId}:`, error);
        }
      }
    });

    if (componentsToRefresh.length > 0) {
      logger.debug(`📊 ChangePool: Refreshed ${componentsToRefresh.length} components:`, componentsToRefresh);
    } else {
      logger.debug(`📊 ChangePool: No components needed refresh for ${notification.entityType} ${notification.eventType}`);
    }
  }

  /**
   * Determine if a component should be refreshed based on the notification
   */
  private shouldComponentRefresh(
    subscription: ComponentSubscription,
    notification: ChangeNotification
  ): boolean {
    // Check if component cares about this entity type
    if (!subscription.entityTypes.includes(notification.entityType)) {
      return false;
    }

    // Check specific entity IDs if provided
    if (subscription.entityIds && subscription.entityIds.length > 0) {
      if (!subscription.entityIds.includes(notification.entityId)) {
        return false;
      }
    }

    // Check project filter
    if (subscription.projectId && notification.metadata?.project_id) {
      if (subscription.projectId !== notification.metadata.project_id) {
        return false;
      }
    }

    // Check branch filter
    if (subscription.branchId && notification.metadata?.git_branch_id) {
      if (subscription.branchId !== notification.metadata.git_branch_id) {
        return false;
      }
    }

    // Apply custom filter if provided
    if (subscription.shouldRefresh) {
      return subscription.shouldRefresh(notification);
    }

    return true;
  }

  /**
   * Get recent changes for debugging
   */
  getChangeHistory(): ChangeNotification[] {
    return [...this.changeHistory];
  }

  /**
   * Get current subscriptions for debugging
   */
  getSubscriptions(): ComponentSubscription[] {
    return Array.from(this.subscriptions.values());
  }

  /**
   * Clear all subscriptions (useful for cleanup)
   */
  clearAllSubscriptions(): void {
    logger.debug(`📡 ChangePool: Clearing all ${this.subscriptions.size} subscriptions`);
    this.subscriptions.clear();
  }

  /**
   * Force refresh all components subscribed to specific entity types
   */
  forceRefresh(entityTypes: EntityType[]): void {
    logger.debug(`📡 ChangePool: Force refreshing components for ${entityTypes.join(', ')}`);

    this.subscriptions.forEach((subscription, componentId) => {
      const hasMatchingType = subscription.entityTypes.some(type => entityTypes.includes(type));

      if (hasMatchingType) {
        try {
          subscription.refreshCallback();
          logger.debug(`✅ ChangePool: Force refreshed ${componentId}`);
        } catch (error) {
          logger.error(`❌ ChangePool: Failed to force refresh ${componentId}:`, error);
        }
      }
    });
  }
}

// Export singleton instance
export const changePoolService = new ChangePoolService();

// Auto-connect to WebSocket service when this module is imported
if (typeof window !== 'undefined') {
  import('./websocketService').then(({ websocketService }) => {
    // Subscribe to all WebSocket messages and process them through change pool
    const unsubscribe = websocketService.on('*', (message) => {
      // Only process status_update messages (data changes)
      if (message.type === 'status_update' && message.metadata?.entity_type) {
        const notification: ChangeNotification = {
          entityType: message.metadata.entity_type as EntityType,
          entityId: message.metadata.entity_id || 'unknown',
          eventType: (message.metadata.event_type || message.event_type || 'updated') as EventType,
          userId: message.user_id || 'system',
          data: message.data,
          metadata: message.metadata,
          timestamp: message.metadata.timestamp || new Date().toISOString()
        };

        changePoolService.processChange(notification);
      }
    });

    logger.info('📡 ChangePool: Connected to WebSocket service');

    // Cleanup on window unload
    window.addEventListener('beforeunload', () => {
      unsubscribe();
      changePoolService.clearAllSubscriptions();
    });
  }).catch(logger.error);
}