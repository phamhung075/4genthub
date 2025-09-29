/**
 * WebSocket Animation Service - Refactored
 *
 * This service handles ONLY visual animations for WebSocket events.
 * It does NOT handle notifications - that's the responsibility of WebSocketNotificationService.
 * Uses centralized AnimationFactory for all animation coordination.
 * Follows single responsibility principle for clean architecture.
 */

import { WSMessage } from './WebSocketClient';
import { animationFactory, AnimationType } from './AnimationFactory';

export type AnimationTriggerType = 'created' | 'updated' | 'deleted' | 'completed';

export interface AnimationEvent {
  type: AnimationTriggerType;
  entity: string;
  entityId: string;
  data?: any;
  metadata?: any;
}

class WebSocketAnimationService {
  private animationListeners: Map<string, Set<Function>> = new Map();

  /**
   * Initialize the service by connecting to WebSocket message events
   */
  init(webSocketClient: any) {
    console.log('🎬 WebSocketAnimationService: Initializing...');
    console.log('🎬 WebSocketAnimationService: Client type:', typeof webSocketClient);
    console.log('🎬 WebSocketAnimationService: Client has "on" method:', typeof webSocketClient.on);

    // Listen for WebSocket update messages
    webSocketClient.on('update', (message: WSMessage) => {
      console.log('🎬 WebSocketAnimationService: 📨 Received update message');
      this.handleWebSocketMessage(message);
    });

    console.log('✅ WebSocketAnimationService: Connected to WebSocket events');
  }

  /**
   * Handle incoming WebSocket messages and trigger animations
   * Made public for debugging purposes
   */
  handleWebSocketMessage(message: WSMessage) {
    const { payload } = message;
    const { entity, action } = payload;

    console.log('🎬 🚨 DELETE DEBUG: WebSocketAnimationService: Processing message:', {
      entity,
      action,
      messageId: message.id
    });

    // Special detailed logging for DELETE operations
    if (action?.toLowerCase().includes('delete')) {
      console.warn('🗑️ DELETE MESSAGE RECEIVED in WebSocketAnimationService:');
      console.warn('  Entity:', entity);
      console.warn('  Action:', action);
      console.warn('  Message ID:', message.id);
      console.warn('  Full message:', message);
      console.warn('  Checking if entity matches supported types (task/subtask/branch)...');
    }

    // Only handle task-related operations that should trigger animations
    if (entity === 'task') {
      if (action?.toLowerCase().includes('delete')) {
        console.warn('🗑️ DELETE: Triggering task animation');
      }
      this.triggerTaskAnimation(action, message);
    } else if (entity === 'subtask') {
      if (action?.toLowerCase().includes('delete')) {
        console.warn('🗑️ DELETE: Triggering subtask animation');
      }
      this.triggerSubtaskAnimation(action, message);
    } else if (entity === 'branch') {
      if (action?.toLowerCase().includes('delete')) {
        console.warn('🗑️ DELETE: Triggering branch animation');
      }
      this.triggerBranchAnimation(action, message);
    } else {
      if (action?.toLowerCase().includes('delete')) {
        console.warn('🗑️ DELETE: Entity not supported for animations:', entity);
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

    console.log('🎯 WebSocketAnimationService: Triggering task animation via AnimationFactory:', {
      action,
      taskTitle,
      branchTitle
    });

    // Extract task ID from message for targeted animations
    // Try multiple extraction paths to handle different backend message formats
    const primaryId = message.payload?.data?.primary?.id;
    const directDataId = message.payload?.data?.id;
    const metadataId = message.metadata?.entity_id;
    const taskId = primaryId || directDataId || metadataId;

    console.log('🔍 Task ID extraction debug:', {
      primaryId,
      directDataId,
      metadataId,
      finalTaskId: taskId,
      action
    });

    if (!taskId) {
      console.warn('❌ No task ID found - cannot trigger targeted animation');
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
        console.log('🎬 WebSocketAnimationService: Unknown task action:', action);
        return;
    }

    // Trigger animation via centralized factory
    const success = animationFactory.animate(taskId, animationType, 'websocket');

    console.log('🎬 WebSocketAnimationService: Animation request result:', {
      taskId,
      animationType,
      success
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

    console.log('🎯 WebSocketAnimationService: Triggering subtask animation via AnimationFactory:', {
      action,
      subtaskTitle,
      parentTaskTitle
    });

    // Extract subtask ID from message for targeted animations
    const primaryId = message.payload?.data?.primary?.id;
    const directDataId = message.payload?.data?.id;
    const metadataId = message.metadata?.entity_id;
    const subtaskId = primaryId || directDataId || metadataId;

    if (!subtaskId) {
      console.warn('❌ No subtask ID found - cannot trigger targeted animation');
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
        console.log('🎬 WebSocketAnimationService: Unknown subtask action:', action);
        return;
    }

    // Trigger animation via centralized factory
    const success = animationFactory.animate(subtaskId, animationType, 'websocket');

    console.log('🎬 WebSocketAnimationService: Subtask animation request result:', {
      subtaskId,
      animationType,
      success
    });
  }

  /**
   * Trigger animations for branch operations using centralized AnimationFactory
   */
  private triggerBranchAnimation(action: string, message: WSMessage) {
    const { metadata } = message;
    const branchTitle = metadata?.branch_title || 'Branch';

    console.log('🎯 WebSocketAnimationService: Triggering branch animation via AnimationFactory:', {
      action,
      branchTitle
    });

    // Extract branch ID from message for targeted animations
    const primaryId = message.payload?.data?.primary?.id;
    const directDataId = message.payload?.data?.id;
    const metadataId = message.metadata?.entity_id;
    const branchId = primaryId || directDataId || metadataId;

    if (!branchId) {
      console.warn('❌ No branch ID found - cannot trigger targeted animation');
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
        console.log('🎬 WebSocketAnimationService: Unknown branch action:', action);
        return;
    }

    // Trigger animation via centralized factory
    const success = animationFactory.animate(branchId, animationType, 'websocket');

    console.log('🎬 WebSocketAnimationService: Branch animation request result:', {
      branchId,
      animationType,
      success
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
    console.log('🧪 WebSocketAnimationService: Triggering test animation via AnimationFactory:', {
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
        console.warn('🧪 Unknown test animation type:', type);
        return;
    }

    // Trigger animation directly via factory
    const success = animationFactory.animate(elementId, animationType, 'websocket');

    console.log('🧪 Test animation result:', {
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
  console.log('🎬 WebSocketAnimationService: Exposed to window.webSocketAnimationService for debugging');
}