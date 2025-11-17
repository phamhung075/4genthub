/**
 * WebSocket Animation Service - Refactored
 *
 * This service handles ONLY visual animations for WebSocket events.
 * It does NOT handle notifications - that's handled by useRealtimeSync with direct toast hooks.
 * Uses centralized AnimationFactory for all animation coordination.
 * Follows single responsibility principle for clean architecture.
 */

import type { WSMessage } from '../types/websocketTypes';
import { animationFactory, AnimationType } from './AnimationFactory';
import type { AnimationTriggerType } from '../types/serviceTypes';
import logger from '../utils/logger';

class WebSocketAnimationService {
  private animationListeners: Map<string, Set<Function>> = new Map();
  private initialized: boolean = false;
  private updateHandler: ((message: WSMessage) => void) | null = null;

  /**
   * Initialize the service by connecting to WebSocket message events
   * Protected against multiple initialization to prevent duplicate animations
   */
  init(webSocketClient: any) {
    // Prevent duplicate initialization
    if (this.initialized) {
      logger.debug('[WebSocketAnimationService] Already initialized, skipping duplicate init');
      return;
    }

    // Create handler function once and store reference
    this.updateHandler = (message: WSMessage) => {
      this.handleWebSocketMessage(message);
    };

    // Listen for WebSocket update messages
    webSocketClient.on('update', this.updateHandler);

    this.initialized = true;
    logger.debug('[WebSocketAnimationService] Initialized successfully');
  }

  /**
   * Handle incoming WebSocket messages and trigger animations
   */
  handleWebSocketMessage(message: WSMessage) {
    const { payload } = message;
    const { entity, action } = payload;

    // Route to appropriate entity animation handler
    if (entity === 'task') {
      this.triggerTaskAnimation(action, message);
    } else if (entity === 'subtask') {
      this.triggerSubtaskAnimation(action, message);
    } else if (entity === 'branch') {
      this.triggerBranchAnimation(action, message);
    } else if (entity === 'project') {
      this.triggerProjectAnimation(action, message);
    }
  }

  /**
   * Trigger animations for task operations using centralized AnimationFactory
   */
  private triggerTaskAnimation(action: string, message: WSMessage) {
    // Extract task ID from message for targeted animations
    // Try multiple extraction paths to handle different backend message formats
    const primary = message.payload?.data?.primary;
    const primaryId = primary && !Array.isArray(primary) ? primary.id : undefined;
    const directDataId = message.payload?.data?.id;
    const metadataId = message.metadata?.entity_id;
    const taskId = primaryId || directDataId || metadataId;

    if (!taskId) {
      logger.warn('No task ID found - cannot trigger animation');
      return;
    }

    // Map WebSocket actions to animation types
    let animationType: AnimationType | null = null;
    switch (action) {
      case 'created':
<<<<<<< HEAD
        // SKIP animation for created events - mount animation handles this
        // Prevents race condition where WebSocket animation fires before element registration
        return; // Exit early - no animation needed
=======
        animationType = 'create';
        break;
>>>>>>> 8daef02e (fix(project): resolve project creation validation errors and animation issues)
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
        return;
    }

    // Defer animation until after DOM element exists
    // WebSocket event → React renders → DOM updated → Animate
    // Use requestAnimationFrame + setTimeout to ensure React has rendered
    requestAnimationFrame(() => {
      setTimeout(() => {
        animationFactory.animate(taskId, animationType!, 'websocket');
      }, 150); // 150ms delay ensures DOM is ready (React render + paint)
    });

    // Emit event for listeners (backwards compatibility)
    this.emit(`task-${action}`, { action, message });
  }

  /**
   * Trigger animations for subtask operations using centralized AnimationFactory
   */
  private triggerSubtaskAnimation(action: string, message: WSMessage) {
    // Extract subtask ID from message for targeted animations
    const primary = message.payload?.data?.primary;
    const primaryId = primary && !Array.isArray(primary) ? primary.id : undefined;
    const directDataId = message.payload?.data?.id;
    const metadataId = message.metadata?.entity_id;
    const subtaskId = primaryId || directDataId || metadataId;

    if (!subtaskId) {
      logger.warn('No subtask ID found - cannot trigger animation');
      return;
    }

    // Map WebSocket actions to animation types (same mapping as tasks)
    let animationType: AnimationType | null = null;
    switch (action) {
      case 'created':
        // SKIP animation for created events - mount animation handles this
        return; // Exit early - no animation needed
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
        return;
    }

    // Defer animation until after DOM element exists
    requestAnimationFrame(() => {
      setTimeout(() => {
        animationFactory.animate(subtaskId, animationType!, 'websocket');
      }, 150); // 150ms delay ensures DOM is ready
    });
  }

  /**
   * Trigger animations for branch operations using centralized AnimationFactory
   */
  private triggerBranchAnimation(action: string, message: WSMessage) {
    // Extract branch ID from message for targeted animations
    const primary = message.payload?.data?.primary;
    const primaryId = primary && !Array.isArray(primary) ? primary.id : undefined;
    const directDataId = message.payload?.data?.id;
    const metadataId = message.metadata?.entity_id;
    const branchId = primaryId || directDataId || metadataId;

    if (!branchId) {
      logger.warn('No branch ID found - cannot trigger animation');
      return;
    }

    // Map WebSocket actions to animation types (same mapping as tasks)
    let animationType: AnimationType | null = null;

    switch (action) {
      case 'created':
        // SKIP animation for created events - mount animation handles this
        // Prevents race condition and prevents all branches from animating when cache updates
        return; // Exit early - no animation needed
      case 'updated':
        animationType = 'update';
        break;
      case 'delete':
      case 'deleted':
        animationType = 'delete';
        break;
      default:
        return;
    }

    // Defer animation until after DOM element exists
    requestAnimationFrame(() => {
      setTimeout(() => {
        animationFactory.animate(branchId, animationType!, 'websocket');
      }, 150);
    });
  }

  /**
   * Trigger animations for project operations using centralized AnimationFactory
   */
  private triggerProjectAnimation(action: string, message: WSMessage) {
    // Extract project ID from message for targeted animations
    const primary = message.payload?.data?.primary;
    const primaryId = primary && !Array.isArray(primary) ? primary.id : undefined;
    const directDataId = message.payload?.data?.id;
    const metadataId = message.metadata?.entity_id;
    const projectId = primaryId || directDataId || metadataId;

    if (!projectId) {
      logger.warn('No project ID found - cannot trigger animation');
      return;
    }

    // Map WebSocket actions to animation types
    let animationType: AnimationType | null = null;

    switch (action) {
      case 'created':
        // SKIP animation for created events - mount animation handles this
        // Prevents race condition and prevents all projects from animating when cache updates
        return; // Exit early - no animation needed
      case 'updated':
        animationType = 'update';
        break;
      case 'delete':
      case 'deleted':
        animationType = 'delete';
        break;
      default:
        return;
    }

    // Defer animation until after DOM element exists
    requestAnimationFrame(() => {
      setTimeout(() => {
        animationFactory.animate(projectId, animationType!, 'websocket');
      }, 150);
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
