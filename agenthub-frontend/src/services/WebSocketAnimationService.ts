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

    // Extract task ID from message for targeted animations
    const taskId = message.payload?.data?.primary?.id || message.payload?.entity_id;

    switch (action) {
      case 'created':
        // Show success toast with animation
        toastEventBus.success(
          'Task Created',
          `"${taskTitle}" was added to ${branchTitle}`
        );
        // Trigger visual effects with task ID
        this.triggerShimmerEffect('task-created', taskId);
        this.emit('task-created', { action, message });
        break;

      case 'updated':
        // Show info toast for updates
        toastEventBus.info(
          'Task Updated',
          `"${taskTitle}" was modified`
        );
        // Trigger visual effects with task ID
        this.triggerShimmerEffect('task-updated', taskId);
        this.emit('task-updated', { action, message });
        break;

      case 'completed':
        // Show success toast for completion
        toastEventBus.success(
          'Task Completed',
          `"${taskTitle}" was completed successfully`
        );
        // Trigger celebration effect with task ID
        this.triggerCelebrationEffect(taskId);
        this.emit('task-completed', { action, message });
        break;

      case 'deleted':
        console.warn('🗑️ DELETE CASE MATCHED in triggerTaskAnimation');
        console.warn('  Task ID:', taskId);
        console.warn('  Task Title:', taskTitle);
        console.warn('  Branch Title:', branchTitle);
        console.warn('  About to show warning toast...');

        // Show warning toast for deletion
        toastEventBus.warning(
          'Task Deleted',
          `"${taskTitle}" was removed`
        );

        console.warn('✅ DELETE toast triggered');
        console.warn('  About to trigger fade effect...');

        // Trigger fade effect with task ID for targeted animation
        this.triggerFadeEffect(taskId);

        console.warn('✅ DELETE fade effect triggered');
        console.warn('  About to emit task-deleted event...');

        this.emit('task-deleted', { action, message });

        console.warn('✅ DELETE task-deleted event emitted');
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
  private triggerShimmerEffect(eventType: string, taskId?: string) {
    console.log('✨ WebSocketAnimationService: Triggering shimmer effect:', eventType, 'for task:', taskId);

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
      detail: {
        type: eventType,
        timestamp: Date.now(),
        taskId: taskId
      }
    }));
  }

  /**
   * Trigger celebration effect for completed tasks
   */
  private triggerCelebrationEffect(taskId?: string) {
    console.log('🎉 WebSocketAnimationService: Triggering celebration effect for task:', taskId);

    // Add celebration class to body for global effects
    document.body.classList.add('task-celebration');

    // Remove after animation
    setTimeout(() => {
      document.body.classList.remove('task-celebration');
    }, 3000);

    // Dispatch celebration event with task ID
    window.dispatchEvent(new CustomEvent('task-celebration', {
      detail: {
        timestamp: Date.now(),
        taskId: taskId
      }
    }));
  }

  /**
   * Trigger fade effect for deleted items
   */
  private triggerFadeEffect(taskId?: string) {
    console.warn('💨 🗑️ DELETE: WebSocketAnimationService: Triggering fade effect for task:', taskId);

    // Check if there are any listeners for the task-fade event
    console.warn('  About to dispatch task-fade CustomEvent...');
    console.warn('  Task ID:', taskId);
    console.warn('  Timestamp:', Date.now());

    // Dispatch fade event with task ID
    const event = new CustomEvent('task-fade', {
      detail: {
        timestamp: Date.now(),
        taskId: taskId
      }
    });

    console.warn('  CustomEvent created:', event);
    console.warn('  Event detail:', event.detail);

    window.dispatchEvent(event);

    console.warn('✅ DELETE task-fade CustomEvent dispatched to window');
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