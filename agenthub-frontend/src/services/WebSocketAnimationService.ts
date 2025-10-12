/**
 * WebSocket Animation Service - Refactored
 *
 * This service handles ONLY visual animations for WebSocket events.
 * It does NOT handle notifications - that's the responsibility of WebSocketNotificationService.
 * Uses centralized AnimationFactory for all animation coordination.
 * Follows single responsibility principle for clean architecture.
 */

import type { WSMessage } from '../types/websocketTypes';
import { animationFactory, AnimationType } from './AnimationFactory';
import type { AnimationTriggerType } from '../types/serviceTypes';
import logger from '../utils/logger';

class WebSocketAnimationService {
  private animationListeners: Map<string, Set<Function>> = new Map();

  /**
   * Initialize the service by connecting to WebSocket message events
   */
  init(webSocketClient: any) {
    logger.debug('🎬 WebSocketAnimationService: Initializing...');
    logger.debug('🎬 WebSocketAnimationService: Client type:', typeof webSocketClient);
    logger.debug('🎬 WebSocketAnimationService: Client has "on" method:', typeof webSocketClient.on);

    // Listen for WebSocket update messages
    webSocketClient.on('update', (message: WSMessage) => {
      logger.debug('🎬 WebSocketAnimationService: 📨 Received update message');
      this.handleWebSocketMessage(message);
    });

    logger.debug('✅ WebSocketAnimationService: Connected to WebSocket events');
  }

  /**
   * Handle incoming WebSocket messages and trigger animations
   * Made public for debugging purposes
   */
  handleWebSocketMessage(message: WSMessage) {
    const { payload } = message;
    const { entity, action } = payload;

    logger.debug('🎬 🚨 DELETE DEBUG: WebSocketAnimationService: Processing message:', {
      entity,
      action,
      messageId: message.id
    });

    // Special detailed logging for DELETE operations
    if (action?.toLowerCase().includes('delete')) {
      logger.warn('🗑️ DELETE MESSAGE RECEIVED in WebSocketAnimationService:');
      logger.warn('  Entity:', entity);
      logger.warn('  Action:', action);
      logger.warn('  Message ID:', message.id);
      logger.warn('  Full message:', message);
      logger.warn('  Checking if entity matches supported types (task/subtask/branch)...');
    }

    // Only handle task-related operations that should trigger animations
    if (entity === 'task') {
      if (action?.toLowerCase().includes('delete')) {
        logger.warn('🗑️ DELETE: Triggering task animation');
      }
      this.triggerTaskAnimation(action, message);
    } else if (entity === 'subtask') {
      if (action?.toLowerCase().includes('delete')) {
        logger.warn('🗑️ DELETE: Triggering subtask animation');
      }
      this.triggerSubtaskAnimation(action, message);
    } else if (entity === 'branch') {
      if (action?.toLowerCase().includes('delete')) {
        logger.warn('🗑️ DELETE: Triggering branch animation');
      }
      this.triggerBranchAnimation(action, message);
    } else {
      if (action?.toLowerCase().includes('delete')) {
        logger.warn('🗑️ DELETE: Entity not supported for animations:', entity);
      }
    }
  }

  /**
   * Trigger animations for task operations using centralized AnimationFactory
   */
  private triggerTaskAnimation(action: string, message: WSMessage) {
    const { metadata } = message;
    const taskTitle = metadata?.task_title || 'Task';
    const branchTitle = metadata?.parent_branch_title || 'Branch';

    logger.debug('🎯 WebSocketAnimationService: Triggering task animation via AnimationFactory:', {
      action,
      taskTitle,
      branchTitle
    });

    // Extract task ID from message for targeted animations
    // Try multiple extraction paths to handle different backend message formats
    const primary = message.payload?.data?.primary;
    const primaryId = primary && !Array.isArray(primary) ? primary.id : undefined;
    const directDataId = message.payload?.data?.id;
    const metadataId = message.metadata?.entity_id;
    const taskId = primaryId || directDataId || metadataId;

    logger.debug('🔍 Task ID extraction debug:', {
      primaryId,
      directDataId,
      metadataId,
      finalTaskId: taskId,
      action
    });

    if (!taskId) {
      logger.warn('❌ No task ID found - cannot trigger targeted animation');
      return;
    }

    // Map WebSocket actions to animation types
    let animationType: AnimationType | null = null;
    switch (action) {
      case 'created':
        animationType = 'create';
        break;
      case 'updated':
        animationType = 'update';
        break;
      case 'completed':
        animationType = 'complete';
        break;
      case 'delete':
      case 'deleted':
        animationType = 'delete';
        break;
      default:
        logger.debug('🎬 WebSocketAnimationService: Unknown task action:', action);
        return;
    }

    // FIX: Defer animation until after DOM element exists
    // WebSocket event → React renders → DOM updated → Animate
    // Use requestAnimationFrame + setTimeout to ensure React has rendered
    requestAnimationFrame(() => {
      setTimeout(() => {
        // Trigger animation via centralized factory
        const success = animationFactory.animate(taskId, animationType!, 'websocket');

        logger.debug('🎬 WebSocketAnimationService: Animation request result (deferred):', {
          taskId,
          animationType,
          success
        });
      }, 150); // 150ms delay ensures DOM is ready (React render + paint)
    });

    // Emit event for listeners (backwards compatibility)
    this.emit(`task-${action}`, { action, message });
  }

  /**
   * Trigger animations for subtask operations using centralized AnimationFactory
   */
  private triggerSubtaskAnimation(action: string, message: WSMessage) {
    const { metadata } = message;
    const subtaskTitle = metadata?.subtask_title || 'Subtask';
    const parentTaskTitle = metadata?.parent_task_title || 'Task';

    logger.debug('🎯 WebSocketAnimationService: Triggering subtask animation via AnimationFactory:', {
      action,
      subtaskTitle,
      parentTaskTitle
    });

    // Extract subtask ID from message for targeted animations
    const primary = message.payload?.data?.primary;
    const primaryId = primary && !Array.isArray(primary) ? primary.id : undefined;
    const directDataId = message.payload?.data?.id;
    const metadataId = message.metadata?.entity_id;
    const subtaskId = primaryId || directDataId || metadataId;

    if (!subtaskId) {
      logger.warn('❌ No subtask ID found - cannot trigger targeted animation');
      return;
    }

    // Map WebSocket actions to animation types (same mapping as tasks)
    let animationType: AnimationType | null = null;
    switch (action) {
      case 'created':
        animationType = 'create';
        break;
      case 'updated':
        animationType = 'update';
        break;
      case 'completed':
        animationType = 'complete';
        break;
      case 'delete':
      case 'deleted':
        animationType = 'delete';
        break;
      default:
        logger.debug('🎬 WebSocketAnimationService: Unknown subtask action:', action);
        return;
    }

    // FIX: Defer animation until after DOM element exists
    requestAnimationFrame(() => {
      setTimeout(() => {
        // Trigger animation via centralized factory
        const success = animationFactory.animate(subtaskId, animationType!, 'websocket');

        logger.debug('🎬 WebSocketAnimationService: Subtask animation request result (deferred):', {
          subtaskId,
          animationType,
          success
        });
      }, 150); // 150ms delay ensures DOM is ready
    });
  }

  /**
   * Trigger animations for branch operations using centralized AnimationFactory
   */
  private triggerBranchAnimation(action: string, message: WSMessage) {
    const { metadata } = message;
    const branchTitle = metadata?.branch_title || 'Branch';

    logger.debug('🎯 WebSocketAnimationService: Triggering branch animation via AnimationFactory:', {
      action,
      branchTitle
    });

    // Extract branch ID from message for targeted animations
    const primary = message.payload?.data?.primary;
    const primaryId = primary && !Array.isArray(primary) ? primary.id : undefined;
    const directDataId = message.payload?.data?.id;
    const metadataId = message.metadata?.entity_id;
    const branchId = primaryId || directDataId || metadataId;

    if (!branchId) {
      logger.warn('❌ No branch ID found - cannot trigger targeted animation');
      return;
    }

    // Map WebSocket actions to animation types (same mapping as tasks)
    let animationType: AnimationType | null = null;
    switch (action) {
      case 'created':
        animationType = 'create';
        break;
      case 'updated':
        animationType = 'update';
        break;
      case 'delete':
      case 'deleted':
        animationType = 'delete';
        break;
      default:
        logger.debug('🎬 WebSocketAnimationService: Unknown branch action:', action);
        return;
    }

    // FIX: Defer animation until after DOM element exists
    requestAnimationFrame(() => {
      setTimeout(() => {
        // Trigger animation via centralized factory
        const success = animationFactory.animate(branchId, animationType!, 'websocket');

        logger.debug('🎬 WebSocketAnimationService: Branch animation request result (deferred):', {
          branchId,
          animationType,
          success
        });
      }, 150); // 150ms delay ensures DOM is ready
    });
  }

  // REMOVED: All direct animation methods replaced by centralized AnimationFactory
  // - triggerFadeInAnimation
  // - triggerFadeOutAnimation
  // - triggerContentUpdateAnimation
  // - triggerCelebrationEffect
  //
  // These are now handled by AnimationFactory.animate() with proper coordination


  /**
   * Subscribe to animation events
   */
  on(eventType: string, callback: Function): () => void {
    if (!this.animationListeners.has(eventType)) {
      this.animationListeners.set(eventType, new Set());
    }
    this.animationListeners.get(eventType)!.add(callback);

    // Return unsubscribe function
    return () => {
      this.animationListeners.get(eventType)?.delete(callback);
    };
  }

  /**
   * Emit animation events to listeners
   */
  private emit(eventType: string, data: any) {
    const listeners = this.animationListeners.get(eventType);
    if (listeners) {
      listeners.forEach(listener => listener(data));
    }
  }

  /**
   * Manually trigger an animation (for testing) - now uses AnimationFactory
   */
  triggerTestAnimation(type: AnimationTriggerType, entity: string = 'task', elementId: string = 'test-element') {
    logger.debug('🧪 WebSocketAnimationService: Triggering test animation via AnimationFactory:', {
      type,
      entity,
      elementId
    });

    // Map animation trigger type to AnimationType
    let animationType: AnimationType;
    switch (type) {
      case 'created':
        animationType = 'create';
        break;
      case 'updated':
        animationType = 'update';
        break;
      case 'deleted':
        animationType = 'delete';
        break;
      case 'completed':
        animationType = 'complete';
        break;
      default:
        logger.warn('🧪 Unknown test animation type:', type);
        return;
    }

    // Trigger animation directly via factory
    const success = animationFactory.animate(elementId, animationType, 'websocket');

    logger.debug('🧪 Test animation result:', {
      elementId,
      animationType,
      success
    });

    // Also emit event for backwards compatibility
    this.emit(`${entity}-${type}`, {
      action: type,
      message: {
        id: `test-${Date.now()}`,
        payload: { entity, action: type },
        metadata: { entity_id: elementId }
      }
    });
  }
}

// Export singleton instance
export const webSocketAnimationService = new WebSocketAnimationService();

// DEBUG: Export to window for debugging and testing
if (typeof window !== 'undefined') {
  (window as any).webSocketAnimationService = webSocketAnimationService;
  logger.debug('🎬 WebSocketAnimationService: Exposed to window.webSocketAnimationService for debugging');
}