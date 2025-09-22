/**
 * WebSocket Notification Service
 *
 * This service bridges WebSocket events to toast notifications.
 * It listens to WebSocket messages and triggers appropriate toast notifications
 * for CREATE, UPDATE, and DELETE operations.
 */

import { notificationService } from './notificationService';
import logger from '../utils/logger';

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

class WebSocketNotificationService {
  private initialized = false;

  /**
   * Initialize the service with a WebSocket client
   */
  init(webSocketClient: any): () => void {
    if (this.initialized) {
      console.warn('🔔 WebSocketNotificationService: Already initialized');
      return () => {};
    }

    console.log('🔔 WebSocketNotificationService: Initializing...');
    logger.info('🔔 WebSocketNotificationService: Initializing WebSocket notification bridge');

    // Subscribe to WebSocket update messages
    const unsubscribe = webSocketClient.on('update', (message: WSMessage) => {
      this.handleWebSocketMessage(message);
    });

    this.initialized = true;
    console.log('🔔 WebSocketNotificationService: Successfully initialized and subscribed to WebSocket events');
    logger.info('🔔 WebSocketNotificationService: Successfully initialized');

    // Return cleanup function
    return () => {
      console.log('🔔 WebSocketNotificationService: Cleaning up...');
      logger.debug('🔔 WebSocketNotificationService: Cleaning up');

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
        console.warn('🗑️ DELETE MESSAGE SKIPPED by WebSocketNotificationService:');
        console.warn('  Reason: Not update type or from mcp-ai');
        console.warn('  Type:', message.type);
        console.warn('  Source:', message.metadata?.source);
        console.warn('  Action:', message.payload?.action);
      }
      return;
    }

    const { entity, action } = message.payload;
    const data = message.payload.data.primary;

    console.log('🔔 🚨 DELETE DEBUG: WebSocketNotificationService: Processing message:', {
      entity,
      action,
      source: message.metadata?.source,
      messageId: message.id
    });

    // Special detailed logging for DELETE operations
    if (action?.toLowerCase().includes('delete')) {
      console.warn('🗑️ DELETE MESSAGE PROCESSING in WebSocketNotificationService:');
      console.warn('  Entity:', entity);
      console.warn('  Action:', action);
      console.warn('  Source:', message.metadata?.source);
      console.warn('  Message ID:', message.id);
      console.warn('  Data:', data);
      console.warn('  Full message:', message);
    }

    // Map WebSocket actions to notification event types
    const eventType = this.mapActionToEventType(action);
    if (!eventType) {
      if (action?.toLowerCase().includes('delete')) {
        console.warn('🗑️ DELETE ACTION NOT MAPPED:', action);
        console.warn('  Available mappings:', Object.keys({
          'create': 'created', 'created': 'created', 'update': 'updated', 'updated': 'updated',
          'delete': 'deleted', 'deleted': 'deleted', 'complete': 'completed', 'completed': 'completed'
        }));
      } else {
        console.log('🔔 WebSocketNotificationService: Ignoring unmapped action:', action);
      }
      return;
    }

    if (action?.toLowerCase().includes('delete')) {
      console.warn('✅ DELETE ACTION MAPPED SUCCESSFULLY:', action, '→', eventType);
    }

    // Extract entity information
    const entityName = this.extractEntityName(data, entity);
    const entityId = this.extractEntityId(data);
    const userName = this.extractUserName(message.metadata);

    console.log('🔔 🚨 DELETE DEBUG: WebSocketNotificationService: Triggering notification:', {
      entityType: entity,
      eventType,
      entityName,
      entityId,
      userName
    });

    if (action?.toLowerCase().includes('delete')) {
      console.warn('🗑️ DELETE NOTIFICATION TRIGGER DETAILS:');
      console.warn('  Entity Type:', entity);
      console.warn('  Event Type:', eventType);
      console.warn('  Entity Name:', entityName);
      console.warn('  Entity ID:', entityId);
      console.warn('  User Name:', userName);
      console.warn('  About to call notificationService.notifyEntityChange...');
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
        console.warn(`✅ 🗑️ DELETE NOTIFICATION TRIGGERED SUCCESSFULLY: ${eventType} notification for ${entity}`);
      } else {
        console.log(`✅ WebSocketNotificationService: Successfully triggered ${eventType} notification for ${entity}`);
      }
      logger.debug(`✅ WebSocketNotificationService: Triggered ${eventType} notification for ${entity}`);
    } catch (error) {
      if (action?.toLowerCase().includes('delete')) {
        console.error('❌ 🗑️ DELETE NOTIFICATION FAILED:', error);
      } else {
        console.error('❌ WebSocketNotificationService: Failed to trigger notification:', error);
      }
      logger.error('❌ WebSocketNotificationService: Failed to trigger notification:', error);
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