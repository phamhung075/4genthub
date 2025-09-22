/**
 * WebSocket Animation Service
 *
 * This service bridges WebSocket messages to animation triggers.
 * It listens for task operation messages and triggers appropriate visual feedback.
 */

import { WSMessage } from './WebSocketClient';
import { toastEventBus } from './toastEventBus';

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
   */
  private handleWebSocketMessage(message: WSMessage) {
    const { payload, metadata } = message;
    const { entity, action } = payload;

    console.log('🎬 WebSocketAnimationService: Processing message:', {
      entity,
      action,
      messageId: message.id
    });

    // Only handle task-related operations that should trigger animations
    if (entity === 'task') {
      this.triggerTaskAnimation(action, message);
    } else if (entity === 'subtask') {
      this.triggerSubtaskAnimation(action, message);
    } else if (entity === 'branch') {
      this.triggerBranchAnimation(action, message);
    }
  }

  /**
   * Trigger animations for task operations
   */
  private triggerTaskAnimation(action: string, message: WSMessage) {
    const { payload, metadata } = message;
    const taskTitle = metadata?.task_title || 'Task';
    const branchTitle = metadata?.parent_branch_title || 'Branch';

    console.log('🎯 WebSocketAnimationService: Triggering task animation:', {
      action,
      taskTitle,
      branchTitle
    });

    switch (action) {
      case 'created':
        // Show success toast with animation
        toastEventBus.success(
          'Task Created',
          `"${taskTitle}" was added to ${branchTitle}`
        );
        // Trigger visual effects
        this.triggerShimmerEffect('task-created');
        this.emit('task-created', { action, message });
        break;

      case 'updated':
        // Show info toast for updates
        toastEventBus.info(
          'Task Updated',
          `"${taskTitle}" was modified`
        );
        // Trigger visual effects
        this.triggerShimmerEffect('task-updated');
        this.emit('task-updated', { action, message });
        break;

      case 'completed':
        // Show success toast for completion
        toastEventBus.success(
          'Task Completed',
          `"${taskTitle}" was completed successfully`
        );
        // Trigger celebration effect
        this.triggerCelebrationEffect();
        this.emit('task-completed', { action, message });
        break;

      case 'deleted':
        // Show warning toast for deletion
        toastEventBus.warning(
          'Task Deleted',
          `"${taskTitle}" was removed`
        );
        // Trigger fade effect
        this.triggerFadeEffect();
        this.emit('task-deleted', { action, message });
        break;

      default:
        console.log('🎬 WebSocketAnimationService: Unknown task action:', action);
    }
  }

  /**
   * Trigger animations for subtask operations
   */
  private triggerSubtaskAnimation(action: string, message: WSMessage) {
    const { metadata } = message;
    const subtaskTitle = metadata?.subtask_title || 'Subtask';
    const parentTaskTitle = metadata?.parent_task_title || 'Task';

    console.log('🎯 WebSocketAnimationService: Triggering subtask animation:', {
      action,
      subtaskTitle,
      parentTaskTitle
    });

    switch (action) {
      case 'created':
        toastEventBus.info(
          'Subtask Created',
          `"${subtaskTitle}" added to "${parentTaskTitle}"`
        );
        this.triggerShimmerEffect('subtask-created');
        break;

      case 'completed':
        toastEventBus.success(
          'Subtask Completed',
          `"${subtaskTitle}" finished`
        );
        this.triggerShimmerEffect('subtask-completed');
        break;

      default:
        console.log('🎬 WebSocketAnimationService: Unknown subtask action:', action);
    }
  }

  /**
   * Trigger animations for branch operations
   */
  private triggerBranchAnimation(action: string, message: WSMessage) {
    const { metadata } = message;
    const branchTitle = metadata?.branch_title || 'Branch';

    console.log('🎯 WebSocketAnimationService: Triggering branch animation:', {
      action,
      branchTitle
    });

    switch (action) {
      case 'created':
        toastEventBus.success(
          'Branch Created',
          `"${branchTitle}" workspace is ready`
        );
        this.triggerShimmerEffect('branch-created');
        break;

      default:
        console.log('🎬 WebSocketAnimationService: Unknown branch action:', action);
    }
  }

  /**
   * Trigger shimmer effect on UI elements
   */
  private triggerShimmerEffect(eventType: string) {
    console.log('✨ WebSocketAnimationService: Triggering shimmer effect:', eventType);

    // Find shimmer-capable elements and trigger their animations
    const shimmerElements = document.querySelectorAll('.shimmer-button, [data-shimmer]');

    shimmerElements.forEach((element) => {
      // Add temporary shimmer class
      element.classList.add('shimmer-active');

      // Remove after animation duration
      setTimeout(() => {
        element.classList.remove('shimmer-active');
      }, 2500);
    });

    // Dispatch custom event for other components to listen to
    window.dispatchEvent(new CustomEvent('websocket-animation', {
      detail: { type: eventType, timestamp: Date.now() }
    }));
  }

  /**
   * Trigger celebration effect for completed tasks
   */
  private triggerCelebrationEffect() {
    console.log('🎉 WebSocketAnimationService: Triggering celebration effect');

    // Add celebration class to body for global effects
    document.body.classList.add('task-celebration');

    // Remove after animation
    setTimeout(() => {
      document.body.classList.remove('task-celebration');
    }, 3000);

    // Dispatch celebration event
    window.dispatchEvent(new CustomEvent('task-celebration', {
      detail: { timestamp: Date.now() }
    }));
  }

  /**
   * Trigger fade effect for deleted items
   */
  private triggerFadeEffect() {
    console.log('💨 WebSocketAnimationService: Triggering fade effect');

    // Dispatch fade event
    window.dispatchEvent(new CustomEvent('task-fade', {
      detail: { timestamp: Date.now() }
    }));
  }

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
   * Manually trigger an animation (for testing)
   */
  triggerTestAnimation(type: AnimationTriggerType, entity: string = 'task') {
    console.log('🧪 WebSocketAnimationService: Triggering test animation:', type, entity);

    const mockMessage: WSMessage = {
      id: `test-${Date.now()}`,
      version: '2.0',
      type: 'update',
      timestamp: new Date().toISOString(),
      sequence: 1,
      payload: {
        entity,
        action: type,
        data: { primary: { id: 'test-id' } }
      },
      metadata: {
        source: 'user',
        task_title: 'Test Task',
        parent_branch_title: 'Test Branch'
      }
    };

    this.handleWebSocketMessage(mockMessage);
  }
}

// Export singleton instance
export const webSocketAnimationService = new WebSocketAnimationService();