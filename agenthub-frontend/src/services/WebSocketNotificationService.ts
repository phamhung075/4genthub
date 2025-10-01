/**
 * WebSocket Notification Service
 *
 * @deprecated This service has been replaced by unified notification handling in notificationService.ts
 * The new implementation includes automatic deduplication to prevent duplicate notifications.
 *
 * Migration: Use notificationService.initializeWebSocketListener() instead of webSocketNotificationService.init()
 *
 * This service bridges WebSocket events to toast notifications.
 * It listens to WebSocket messages and triggers appropriate toast notifications
 * for CREATE, UPDATE, and DELETE operations.
 */

import { notificationService } from './notificationService';
import logger from '../utils/logger';
import type { EntityType, EventType } from '../types/serviceTypes';

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

class WebSocketNotificationService {
  private initialized = false;

  /**
   * Initialize the service with a WebSocket client
   */
  init(webSocketClient: any): () => void {
    if (this.initialized) {
      logger.warn('🔔 WebSocketNotificationService: Already initialized', undefined, 'WebSocketNotificationService.ts');
      return () => {};
    }

    logger.info('🔔 WebSocketNotificationService: Initializing WebSocket notification bridge', undefined, 'WebSocketNotificationService.ts');

    // Subscribe to WebSocket update messages
    const unsubscribe = webSocketClient.on('update', (message: WSMessage) => {
      this.handleWebSocketMessage(message);
    });

    this.initialized = true;
    logger.info('🔔 WebSocketNotificationService: Successfully initialized and subscribed to WebSocket events', undefined, 'WebSocketNotificationService.ts');

    // Return cleanup function
    return () => {
      logger.debug('🔔 WebSocketNotificationService: Cleaning up...', undefined, 'WebSocketNotificationService.ts');

      if (typeof unsubscribe === 'function') {
        unsubscribe();
      }

      this.initialized = false;
    };
  }

  /**
   * Handle incoming WebSocket messages and trigger appropriate notifications
   */
  private handleWebSocketMessage(message: WSMessage): void {
    // Only process update messages from user actions (not AI batched updates)
    if (message.type !== 'update' || message.metadata?.source === 'mcp-ai') {
      // Log if we're skipping a DELETE message
      if (message.payload?.action?.toLowerCase().includes('delete')) {
        logger.warn('🗑️ DELETE MESSAGE SKIPPED by WebSocketNotificationService:', {
          reason: 'Not update type or from mcp-ai',
          type: message.type,
          source: message.metadata?.source,
          action: message.payload?.action
        }, 'WebSocketNotificationService.ts');
      }
      return;
    }

    const { entity, action } = message.payload;
    const data = message.payload.data.primary;

    logger.debug('🔔 🚨 DELETE DEBUG: WebSocketNotificationService: Processing message:', {
      entity,
      action,
      source: message.metadata?.source,
      messageId: message.id
    }, 'WebSocketNotificationService.ts');

    // Special detailed logging for DELETE operations
    if (action?.toLowerCase().includes('delete')) {
      logger.warn('🗑️ DELETE MESSAGE PROCESSING in WebSocketNotificationService:', {
        entity,
        action,
        source: message.metadata?.source,
        messageId: message.id,
        data,
        fullMessage: message
      }, 'WebSocketNotificationService.ts');
    }

    // Map WebSocket actions to notification event types
    const eventType = this.mapActionToEventType(action);
    if (!eventType) {
      if (action?.toLowerCase().includes('delete')) {
        logger.warn('🗑️ DELETE ACTION NOT MAPPED:', {
          action,
          availableMappings: Object.keys({
            'create': 'created', 'created': 'created', 'update': 'updated', 'updated': 'updated',
            'delete': 'deleted', 'deleted': 'deleted', 'complete': 'completed', 'completed': 'completed'
          })
        }, 'WebSocketNotificationService.ts');
      } else {
        logger.debug('🔔 WebSocketNotificationService: Ignoring unmapped action:', action, 'WebSocketNotificationService.ts');
      }
      return;
    }

    if (action?.toLowerCase().includes('delete')) {
      logger.warn('✅ DELETE ACTION MAPPED SUCCESSFULLY:', { action, eventType }, 'WebSocketNotificationService.ts');
    }

    // Extract entity information
    const entityName = this.extractEntityName(data, entity);
    const entityId = this.extractEntityId(data);
    const userName = this.extractUserName(message.metadata);

    logger.debug('🔔 🚨 DELETE DEBUG: WebSocketNotificationService: Triggering notification:', {
      entityType: entity,
      eventType,
      entityName,
      entityId,
      userName
    }, 'WebSocketNotificationService.ts');

    if (action?.toLowerCase().includes('delete')) {
      logger.warn('🗑️ DELETE NOTIFICATION TRIGGER DETAILS:', {
        entityType: entity,
        eventType,
        entityName,
        entityId,
        userName,
        info: 'About to call notificationService.notifyEntityChange...'
      }, 'WebSocketNotificationService.ts');
    }

    // Trigger notification
    try {
      notificationService.notifyEntityChange(
        entity as EntityType,
        eventType,
        entityName,
        entityId,
        userName
      );

      if (action?.toLowerCase().includes('delete')) {
        logger.warn(`✅ 🗑️ DELETE NOTIFICATION TRIGGERED SUCCESSFULLY: ${eventType} notification for ${entity}`, undefined, 'WebSocketNotificationService.ts');
      } else {
        logger.debug(`✅ WebSocketNotificationService: Successfully triggered ${eventType} notification for ${entity}`, undefined, 'WebSocketNotificationService.ts');
      }
    } catch (error) {
      if (action?.toLowerCase().includes('delete')) {
        logger.error('❌ 🗑️ DELETE NOTIFICATION FAILED:', error, 'WebSocketNotificationService.ts');
      } else {
        logger.error('❌ WebSocketNotificationService: Failed to trigger notification:', error, 'WebSocketNotificationService.ts');
      }
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
   * Check if service is initialized
   */
  isInitialized(): boolean {
    return this.initialized;
  }
}

// Export singleton instance
export const webSocketNotificationService = new WebSocketNotificationService();