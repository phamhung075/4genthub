/**
 * Centralized Change Pool Service
 *
 * This service manages which components need to be refreshed when specific
 * notifications are received from the backend. Components register themselves
 * and specify which entities they care about, then get automatically refreshed
 * when those entities change.
 */

import logger from '../utils/logger';
import type { EntityType, EventType } from '../types/serviceTypes';

/**
 * Extended change notification with additional metadata
 * This extends the base ChangeNotification from serviceTypes with extra fields
 */
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

/**
 * Component subscription configuration for change notifications
 */
export interface ComponentSubscription {
  componentId: string;
  entityTypes: EntityType[];
  entityIds?: string[]; // Specific entity IDs to watch (optional)
  projectId?: string;   // Filter by project
  branchId?: string;    // Filter by branch
  refreshCallback: (notification?: ChangeNotification) => void; // Now accepts optional notification data
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
    logger.debug(`📡 ChangePool: Subscribing ${subscription.componentId} to ${subscription.entityTypes.join(', ')}`, {
      entityTypes: subscription.entityTypes,
      entityIds: subscription.entityIds,
      projectId: subscription.projectId,
      branchId: subscription.branchId
    }, 'changePoolService.ts');

    this.subscriptions.set(subscription.componentId, subscription);
    logger.debug(`📡 ChangePool: Total subscriptions now: ${this.subscriptions.size}`, undefined, 'changePoolService.ts');

    // Return unsubscribe function
    return () => {
      logger.debug(`📡 ChangePool: Unsubscribing ${subscription.componentId}`, undefined, 'changePoolService.ts');
      this.subscriptions.delete(subscription.componentId);
      logger.debug(`📡 ChangePool: Total subscriptions now: ${this.subscriptions.size}`, undefined, 'changePoolService.ts');
    };
  }

  /**
   * Process incoming change notification and refresh relevant components
   */
  processChange(notification: ChangeNotification): void {
    logger.debug(`📡 ChangePool: Processing ${notification.entityType} ${notification.eventType} for ${notification.entityId}`, undefined, 'changePoolService.ts');
    logger.debug(`📡 ChangePool: Current subscriptions count: ${this.subscriptions.size}`, undefined, 'changePoolService.ts');

    // Add to history
    this.changeHistory.unshift(notification);
    if (this.changeHistory.length > this.maxHistorySize) {
      this.changeHistory.pop();
    }

    // Find all components that should be refreshed
    const componentsToRefresh: string[] = [];

    logger.debug('📡 ChangePool: Checking subscriptions for matching components...', undefined, 'changePoolService.ts');
    this.subscriptions.forEach((subscription, componentId) => {
      logger.debug(`📡 ChangePool: Checking subscription ${componentId}:`, {
        entityTypes: subscription.entityTypes,
        entityIds: subscription.entityIds,
        projectId: subscription.projectId,
        branchId: subscription.branchId
      }, 'changePoolService.ts');

      if (this.shouldComponentRefresh(subscription, notification)) {
        componentsToRefresh.push(componentId);
        logger.debug(`✅ ChangePool: Will refresh ${componentId}`, undefined, 'changePoolService.ts');

        // Execute the refresh callback with notification data
        try {
          subscription.refreshCallback(notification);
          logger.debug(`✅ ChangePool: Successfully refreshed ${componentId} for ${notification.entityType} ${notification.eventType} with data`, {
            component: componentId,
            entityType: notification.entityType,
            eventType: notification.eventType
          }, 'changePoolService.ts');
        } catch (error) {
          logger.error(`❌ ChangePool: Failed to refresh ${componentId}:`, {
            component: componentId,
            error
          }, 'changePoolService.ts');
        }
      } else {
        logger.debug(`❌ ChangePool: ${componentId} does not match notification`, undefined, 'changePoolService.ts');
      }
    });

    if (componentsToRefresh.length > 0) {
      logger.info(`📊 ChangePool: Refreshed ${componentsToRefresh.length} component(s) for ${notification.entityType}.${notification.eventType}:`, {
        components: componentsToRefresh,
        entityType: notification.entityType,
        eventType: notification.eventType,
        entityId: notification.entityId
      }, 'changePoolService.ts');
    } else {
      logger.debug(`📊 ChangePool: No components needed refresh for ${notification.entityType} ${notification.eventType}`, undefined, 'changePoolService.ts');
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
          subscription.refreshCallback(); // Force refresh without notification data
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

    logger.debug('📡 ChangePool Subscription Debug', undefined, 'changePoolService.ts');
    logger.debug(`Total subscriptions: ${stats.total}`, undefined, 'changePoolService.ts');
    logger.debug('By component:', stats.byComponent, 'changePoolService.ts');
    logger.debug('By entity type:', stats.byEntityType, 'changePoolService.ts');

    if (stats.potentialDuplicates.length > 0) {
      logger.warn('⚠️ Potential duplicate component patterns:', stats.potentialDuplicates, 'changePoolService.ts');
    }

    if (stats.total > 5) {
      logger.warn(`⚠️ High subscription count: ${stats.total} (expected: 1-3 for typical usage)`, undefined, 'changePoolService.ts');
    }
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
  logger.info('🔌 ChangePool: Initializing WebSocket integration...', undefined, 'changePoolService.ts');
  logger.debug('🔌 ChangePool: WebSocket client type:', typeof webSocketClient, 'changePoolService.ts');
  logger.debug('🔌 ChangePool: WebSocket client has .on:', typeof webSocketClient?.on === 'function', 'changePoolService.ts');

  // Create the handler function so we can reference it later for cleanup
  const updateHandler = (message: any) => {
    logger.debug('📡 ChangePool: ⚡⚡⚡ HANDLER INVOKED ⚡⚡⚡ Received WebSocket update message:', message, 'changePoolService.ts');

    // Process v2.0 protocol messages (check both payload and metadata for entity info)
    if (message.type === 'update' && (message.payload?.entity || message.metadata?.entity_type)) {
      // Extract entity information from v2.0 protocol structure
      const entityType = message.payload?.entity || message.metadata?.entity_type;
      const action = message.payload?.action || message.metadata?.event_type || 'updated';
      // Extract entityId from primary data or metadata
      const entityId = message.payload?.data?.primary?.id || message.metadata?.entity_id || 'unknown';

      // CRITICAL DEBUG: Log data extraction paths
      logger.debug('🔍 [ChangePool] Data extraction debug:', {
        'message.payload?.data?.primary': message.payload?.data?.primary,
        'message.data': message.data,
        'hasPrimary': !!message.payload?.data?.primary,
        'hasMessageData': !!message.data,
        'primaryKeys': message.payload?.data?.primary ? Object.keys(message.payload.data.primary) : [],
        'messageDataKeys': message.data ? Object.keys(message.data) : []
      }, 'changePoolService.ts');

      // FIX: Don't default to empty object - let it be undefined if missing
      const extractedData = message.payload?.data?.primary || message.data;

      // Validate that we have actual task data (not just empty object)
      const hasValidData = extractedData && typeof extractedData === 'object' && Object.keys(extractedData).length > 0;

      logger.debug('🔍 [ChangePool] Extracted data for notification:', {
        hasExtractedData: hasValidData,
        extractedDataKeys: extractedData ? Object.keys(extractedData) : [],
        extractedData: extractedData
      }, 'changePoolService.ts');

      // Warn if no data found in expected locations
      if (!hasValidData) {
        logger.warn('⚠️ [ChangePool] WebSocket message has no valid task data', {
          messageId: message.id,
          entityType,
          entityId,
          action,
          payloadDataPrimary: message.payload?.data?.primary,
          messageData: message.data,
          fullPayload: message.payload
        }, 'changePoolService.ts');
      }

      logger.info('📡 ChangePool: Processing v2.0 update message:', {
        entityType,
        entityId,
        action,
        version: message.version,
        hasData: hasValidData
      }, 'changePoolService.ts');

      const notification: ChangeNotification = {
        entityType: entityType as EntityType,
        entityId: entityId,
        eventType: action as EventType,
        userId: message.metadata?.userId || 'system',
        // Only assign data if it's valid (not undefined and not empty object)
        data: hasValidData ? extractedData : undefined,
        metadata: {
          ...message.metadata,
          // Extract git_branch_id from payload data if available
          git_branch_id: message.payload?.data?.primary?.git_branch_id ||
                         message.payload?.data?.cascade?.git_branch_id ||
                         message.metadata?.git_branch_id
        },
        timestamp: message.timestamp || new Date().toISOString()
      };

      logger.debug('🔍 [ChangePool] Final notification being sent:', {
        entityType: notification.entityType,
        entityId: notification.entityId,
        eventType: notification.eventType,
        hasData: !!notification.data && Object.keys(notification.data).length > 0,
        dataKeys: notification.data ? Object.keys(notification.data) : [],
        data: notification.data
      }, 'changePoolService.ts');

      changePoolService.processChange(notification);
    } else {
      logger.debug('📡 ChangePool: Ignoring non-update message:', {
        type: message.type,
        version: message.version,
        hasPayload: !!message.payload,
        entityType: message.payload?.entity || message.metadata?.entity_type
      }, 'changePoolService.ts');
    }
  };

  // Subscribe to WebSocket update messages
  logger.debug('🔌 ChangePool: About to subscribe to "update" event...', undefined, 'changePoolService.ts');
  webSocketClient.on('update', updateHandler);
  logger.debug('🔌 ChangePool: Subscription complete, checking listener count...', undefined, 'changePoolService.ts');

  // ENHANCED: Smart re-fetch on reconnect
  // When WebSocket reconnects after disconnection, trigger a refresh of all subscriptions
  // to ensure data is up-to-date with any changes that occurred during disconnection
  const connectedHandler = () => {
    // Small delay to ensure WebSocket is fully ready
    setTimeout(() => {
      logger.info('🔄 ChangePool: WebSocket reconnected - triggering data refresh for all subscriptions', undefined, 'changePoolService.ts');

      // Force refresh all active subscriptions
      const stats = changePoolService.getSubscriptionStats();
      logger.debug(`📡 ChangePool: Refreshing ${stats.total} subscriptions after reconnect`, undefined, 'changePoolService.ts');

      // Refresh all entity types currently subscribed
      const entityTypesSet = new Set<EntityType>();
      changePoolService.getSubscriptions().forEach(sub => {
        sub.entityTypes.forEach(type => entityTypesSet.add(type));
      });

      if (entityTypesSet.size > 0) {
        const entityTypes = Array.from(entityTypesSet);
        logger.info(`🔄 ChangePool: Force refreshing components for: ${entityTypes.join(', ')}`, undefined, 'changePoolService.ts');
        changePoolService.forceRefresh(entityTypes);
      }
    }, 100); // 100ms delay to ensure WebSocket is fully connected
  };

  webSocketClient.on('connected', connectedHandler);

  // Verify subscription was successful
  const listenerCount = typeof webSocketClient.listenerCount === 'function'
    ? webSocketClient.listenerCount('update')
    : 'unknown';
  logger.info('📡 ChangePool: Subscribed to WebSocket update events', undefined, 'changePoolService.ts');
  logger.debug('📡 ChangePool: Total update listeners:', listenerCount, 'changePoolService.ts');

  // Return cleanup function
  return () => {
    try {
      // Properly unsubscribe using the off method with the specific handler
      if (webSocketClient && typeof webSocketClient.off === 'function') {
        logger.debug('🔌 ChangePool: Unsubscribing from WebSocket events', undefined, 'changePoolService.ts');
        webSocketClient.off('update', updateHandler);
        webSocketClient.off('connected', connectedHandler);
      } else if (webSocketClient && typeof webSocketClient.removeAllListeners === 'function') {
        // Fallback for EventEmitter-like objects
        logger.debug('🔌 ChangePool: Using removeAllListeners for cleanup', undefined, 'changePoolService.ts');
        webSocketClient.removeAllListeners('update');
        webSocketClient.removeAllListeners('connected');
      } else {
        // Log warning but don't throw - this is not critical
        logger.debug('🔌 ChangePool: WebSocket client cleanup skipped (no suitable method found)', undefined, 'changePoolService.ts');
      }
    } catch (error) {
      // Catch any errors during cleanup to prevent app crashes
      logger.warn('🔌 ChangePool: Error during WebSocket cleanup:', error, 'changePoolService.ts');
    }

    // NOTE: Component subscriptions are managed by useChangeSubscription hook
    // and should NOT be cleared here. This cleanup only removes the WebSocket listener.
    logger.debug('🔌 ChangePool: WebSocket integration cleanup complete (subscriptions preserved)', undefined, 'changePoolService.ts');
  };
}

// Export the initialization function for use in App.tsx or useWebSocket hook
export { initializeWebSocketIntegration };