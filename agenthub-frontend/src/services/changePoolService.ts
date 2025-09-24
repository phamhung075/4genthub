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
    console.log(`📡 ChangePool: Subscribing ${subscription.componentId} to ${subscription.entityTypes.join(', ')}`, {
      entityTypes: subscription.entityTypes,
      entityIds: subscription.entityIds,
      projectId: subscription.projectId,
      branchId: subscription.branchId
    });
    logger.debug(`📡 ChangePool: Subscribing ${subscription.componentId} to ${subscription.entityTypes.join(', ')}`);

    this.subscriptions.set(subscription.componentId, subscription);
    console.log(`📡 ChangePool: Total subscriptions now: ${this.subscriptions.size}`);

    // Return unsubscribe function
    return () => {
      console.log(`📡 ChangePool: Unsubscribing ${subscription.componentId}`);
      logger.debug(`📡 ChangePool: Unsubscribing ${subscription.componentId}`);
      this.subscriptions.delete(subscription.componentId);
      console.log(`📡 ChangePool: Total subscriptions now: ${this.subscriptions.size}`);
    };
  }

  /**
   * Process incoming change notification and refresh relevant components
   */
  processChange(notification: ChangeNotification): void {
    console.log(`📡 ChangePool: Processing ${notification.entityType} ${notification.eventType} for ${notification.entityId}`);
    console.log(`📡 ChangePool: Current subscriptions count: ${this.subscriptions.size}`);
    logger.debug(`📡 ChangePool: Processing ${notification.entityType} ${notification.eventType} for ${notification.entityId}`);

    // Add to history
    this.changeHistory.unshift(notification);
    if (this.changeHistory.length > this.maxHistorySize) {
      this.changeHistory.pop();
    }

    // Find all components that should be refreshed
    const componentsToRefresh: string[] = [];

    console.log('📡 ChangePool: Checking subscriptions for matching components...');
    this.subscriptions.forEach((subscription, componentId) => {
      console.log(`📡 ChangePool: Checking subscription ${componentId}:`, {
        entityTypes: subscription.entityTypes,
        entityIds: subscription.entityIds,
        projectId: subscription.projectId,
        branchId: subscription.branchId
      });

      if (this.shouldComponentRefresh(subscription, notification)) {
        componentsToRefresh.push(componentId);
        console.log(`✅ ChangePool: Will refresh ${componentId}`);

        // Execute the refresh callback
        try {
          subscription.refreshCallback();
          console.log(`✅ ChangePool: Successfully refreshed ${componentId} for ${notification.entityType} ${notification.eventType}`);
          logger.debug(`✅ ChangePool: Refreshed ${componentId} for ${notification.entityType} ${notification.eventType}`);
        } catch (error) {
          console.error(`❌ ChangePool: Failed to refresh ${componentId}:`, error);
          logger.error(`❌ ChangePool: Failed to refresh ${componentId}:`, error);
        }
      } else {
        console.log(`❌ ChangePool: ${componentId} does not match notification`);
      }
    });

    if (componentsToRefresh.length > 0) {
      console.log(`📊 ChangePool: Refreshed ${componentsToRefresh.length} components:`, componentsToRefresh);
      logger.debug(`📊 ChangePool: Refreshed ${componentsToRefresh.length} components:`, componentsToRefresh);
    } else {
      console.log(`📊 ChangePool: No components needed refresh for ${notification.entityType} ${notification.eventType}`);
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

  /**
   * Get subscription statistics for debugging memory leaks
   */
  getSubscriptionStats(): {
    total: number;
    byComponent: Record<string, { entityTypes: EntityType[], hasFilters: boolean }>;
    byEntityType: Record<EntityType, number>;
    potentialDuplicates: string[];
  } {
    const stats = {
      total: this.subscriptions.size,
      byComponent: {} as Record<string, { entityTypes: EntityType[], hasFilters: boolean }>,
      byEntityType: {} as Record<EntityType, number>,
      potentialDuplicates: [] as string[]
    };

    // Analyze each subscription
    this.subscriptions.forEach((subscription, componentId) => {
      // Track by component
      stats.byComponent[componentId] = {
        entityTypes: subscription.entityTypes,
        hasFilters: !!(subscription.projectId || subscription.branchId || subscription.entityIds)
      };

      // Track by entity type
      subscription.entityTypes.forEach(entityType => {
        stats.byEntityType[entityType] = (stats.byEntityType[entityType] || 0) + 1;
      });

      // Detect potential duplicates (same component pattern)
      const baseComponentId = componentId.replace(/-[a-f0-9-]+$/i, ''); // Remove UUIDs/IDs
      const existing = Object.keys(stats.byComponent).find(id =>
        id !== componentId && id.replace(/-[a-f0-9-]+$/i, '') === baseComponentId
      );
      if (existing && !stats.potentialDuplicates.includes(baseComponentId)) {
        stats.potentialDuplicates.push(baseComponentId);
      }
    });

    return stats;
  }

  /**
   * Debug method: Log current subscription state
   */
  debugSubscriptions(): void {
    const stats = this.getSubscriptionStats();

    console.group('📡 ChangePool Subscription Debug');
    console.log(`Total subscriptions: ${stats.total}`);
    console.log('By component:', stats.byComponent);
    console.log('By entity type:', stats.byEntityType);

    if (stats.potentialDuplicates.length > 0) {
      console.warn('⚠️ Potential duplicate component patterns:', stats.potentialDuplicates);
    }

    if (stats.total > 5) {
      console.warn(`⚠️ High subscription count: ${stats.total} (expected: 1-3 for typical usage)`);
    }

    console.groupEnd();
  }
}

// Export singleton instance
export const changePoolService = new ChangePoolService();

// Auto-connect to WebSocket service when this module is imported
/**
 * Initialize change pool WebSocket integration
 * This should be called with the WebSocket client instance from useWebSocket hook
 */
function initializeWebSocketIntegration(webSocketClient: any): () => void {
  console.log('🔌 ChangePool: Initializing WebSocket integration...');
  logger.info('🔌 ChangePool: Initializing WebSocket integration');

  // Create the handler function so we can reference it later for cleanup
  const updateHandler = (message: any) => {
    console.log('📡 ChangePool: Received WebSocket update message:', message);
    logger.debug('📡 ChangePool: Received WebSocket update message:', message);

    // Process v2.0 protocol messages (check both payload and metadata for entity info)
    if (message.type === 'update' && (message.payload?.entity || message.metadata?.entity_type)) {
      // Extract entity information from v2.0 protocol structure
      const entityType = message.payload?.entity || message.metadata?.entity_type;
      const action = message.payload?.action || message.metadata?.event_type || 'updated';
      const entityId = message.metadata?.entity_id || 'unknown';

      console.log('📡 ChangePool: Processing v2.0 update message:', {
        entityType,
        entityId,
        action,
        version: message.version
      });
      logger.info('📡 ChangePool: Processing v2.0 update message:', {
        entityType,
        entityId,
        action,
        version: message.version
      });

      const notification: ChangeNotification = {
        entityType: entityType as EntityType,
        entityId: entityId,
        eventType: action as EventType,
        userId: message.metadata?.userId || 'system',
        data: message.payload?.data?.primary || message.data || {},
        metadata: message.metadata,
        timestamp: message.timestamp || new Date().toISOString()
      };

      changePoolService.processChange(notification);
    } else {
      console.log('📡 ChangePool: Ignoring non-update message:', {
        type: message.type,
        version: message.version,
        hasPayload: !!message.payload,
        entityType: message.payload?.entity || message.metadata?.entity_type
      });
      logger.debug('📡 ChangePool: Ignoring non-update message:', {
        type: message.type,
        version: message.version,
        hasPayload: !!message.payload,
        entityType: message.payload?.entity || message.metadata?.entity_type
      });
    }
  };

  // Subscribe to WebSocket update messages
  webSocketClient.on('update', updateHandler);

  console.log('📡 ChangePool: Subscribed to WebSocket update events');
  logger.info('📡 ChangePool: Connected to WebSocket service');

  // Return cleanup function
  return () => {
    try {
      // Properly unsubscribe using the off method with the specific handler
      if (webSocketClient && typeof webSocketClient.off === 'function') {
        console.log('🔌 ChangePool: Unsubscribing from WebSocket events');
        logger.debug('🔌 ChangePool: Unsubscribing from WebSocket events');
        webSocketClient.off('update', updateHandler);
      } else if (webSocketClient && typeof webSocketClient.removeAllListeners === 'function') {
        // Fallback for EventEmitter-like objects
        console.log('🔌 ChangePool: Using removeAllListeners for cleanup');
        webSocketClient.removeAllListeners('update');
      } else {
        // Log warning but don't throw - this is not critical
        console.log('🔌 ChangePool: WebSocket client cleanup skipped (no suitable method found)');
      }
    } catch (error) {
      // Catch any errors during cleanup to prevent app crashes
      console.warn('🔌 ChangePool: Error during WebSocket cleanup:', error);
      logger.warn('🔌 ChangePool: Error during WebSocket cleanup:', error);
    }

    // Always clear subscriptions regardless of WebSocket cleanup success
    console.log('🔌 ChangePool: Clearing all change pool subscriptions');
    logger.debug('🔌 ChangePool: Clearing all change pool subscriptions');
    changePoolService.clearAllSubscriptions();
  };
}

// Export the initialization function for use in App.tsx or useWebSocket hook
export { initializeWebSocketIntegration };