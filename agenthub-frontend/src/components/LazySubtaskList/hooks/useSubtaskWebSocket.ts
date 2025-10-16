// useSubtaskWebSocket hook - Real-time updates for LazySubtaskList
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import { useEffect, useCallback, useState, useRef } from "react";
import { useChangeSubscription } from "../../../hooks/useChangeSubscription";
import type { UseSubtaskWebSocketReturn, SubtaskChangePayload } from "../../../types/subtaskTypes";
import { LOADING_CONFIG } from "../constants/subtaskConstants";
import { debounce } from "../utils/subtaskHelpers";
import logger from "../../../utils/logger";

/**
 * Custom hook for managing WebSocket real-time updates for subtasks
 * Handles subscription lifecycle and change processing
 */
export function useSubtaskWebSocket(
  parentTaskId: string,
  subscriptionEnabled: boolean,
  onSubtaskChanges: () => Promise<void>,
  onSubtaskDeleted?: (subtaskId: string) => void
): UseSubtaskWebSocketReturn {

  const [isConnected, setIsConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Track pending created subtasks to batch refresh calls
  const pendingCreatedSubtasks = useRef<Set<string>>(new Set());
  const createdRefreshTimer = useRef<NodeJS.Timeout | null>(null);

  // Debounced change handler ONLY for update events
  const debouncedHandleUpdates = useCallback(
    debounce(onSubtaskChanges, LOADING_CONFIG.UPDATE_DEBOUNCE_DELAY),
    [onSubtaskChanges]
  );

  /**
   * Handle incoming WebSocket changes
   */
  const handleWebSocketChange = useCallback(async (data: any) => {
    try {
      // Validate change data
      if (!data || typeof data !== 'object') {
        logger.debug('Invalid WebSocket data received:', data);
        return;
      }

      const eventType = data.eventType || data.type;
      const subtaskId = data.entityId || data.subtask?.id;

      logger.debug('Subtask WebSocket change received:', {
        eventType,
        subtaskId,
        parentTaskId: data.subtask?.parent_task_id || data.parent_task_id
      });

      // Check if this change is relevant to our parent task
      const changeParentTaskId = data.subtask?.parent_task_id || data.parent_task_id || data.metadata?.parent_task_id;
      if (changeParentTaskId && changeParentTaskId !== parentTaskId) {
        logger.debug('Change not relevant to this parent task, ignoring');
        return;
      }

      // Handle delete events specially to trigger animations
      if (eventType === 'deleted' && subtaskId && onSubtaskDeleted) {
        logger.debug('🗑️ [useSubtaskWebSocket] Subtask deleted, triggering animation', { subtaskId }, 'useSubtaskWebSocket.ts');
        onSubtaskDeleted(subtaskId);
        // Don't reload immediately - let animation complete
        return;
      }

      // Handle created events by batching them
      // This prevents race conditions when multiple subtasks are created rapidly
      if (eventType === 'created' && subtaskId) {
        logger.debug('✨ [useSubtaskWebSocket] Subtask created, adding to batch', {
          subtaskId,
          batchSize: pendingCreatedSubtasks.current.size + 1
        });

        // Add to pending batch
        pendingCreatedSubtasks.current.add(subtaskId);

        // Clear existing timer
        if (createdRefreshTimer.current) {
          clearTimeout(createdRefreshTimer.current);
        }

        // Set new timer to batch all creates within 800ms window
        // This window is longer to handle MCP-created subtasks which can have 0.5-1s gaps
        createdRefreshTimer.current = setTimeout(async () => {
          const batchSize = pendingCreatedSubtasks.current.size;
          logger.debug('🔄 [useSubtaskWebSocket] Processing batched created events', {
            batchSize,
            subtaskIds: Array.from(pendingCreatedSubtasks.current)
          });

          // Clear the batch before refresh to avoid duplicates
          pendingCreatedSubtasks.current.clear();

          // Single refresh for all created subtasks
          await onSubtaskChanges();
          setReconnectAttempts(0);

          logger.debug('✅ [useSubtaskWebSocket] Batch refresh completed', { batchSize });
        }, 800); // 800ms window to catch MCP-created subtasks with network latency

        return;
      }

      // For update events, use debouncing to prevent rapid updates
      await debouncedHandleUpdates();
      setReconnectAttempts(0);

    } catch (error) {
      logger.error('Error processing WebSocket change:', error);
    }
  }, [parentTaskId, onSubtaskChanges, debouncedHandleUpdates, onSubtaskDeleted]);

  /**
   * Handle connection state changes
   */
  const handleConnectionChange = useCallback((connected: boolean) => {
    setIsConnected(connected);

    if (connected) {
      logger.debug('Subtask WebSocket connected');
      setReconnectAttempts(0);
    } else {
      logger.debug('Subtask WebSocket disconnected');
      setReconnectAttempts(prev => prev + 1);
    }
  }, []);

  /**
   * Subscribe to WebSocket changes using the new API
   * NOTE: For subtasks, we filter by parent_task_id in metadata, not entityIds
   * because entityId in the notification is the subtask ID, not parent task ID
   */
  useChangeSubscription({
    componentId: `LazySubtaskList-${parentTaskId}`,
    entityTypes: ['subtask'],
    // Don't filter by entityIds - let all subtask notifications through
    // We'll filter by parent_task_id in the shouldRefresh custom filter
    shouldRefresh: (notification) => {
      // For subtasks, check if the parent_task_id matches
      const notificationParentTaskId = notification.metadata?.parent_task_id;
      return notificationParentTaskId === parentTaskId;
    },
    refreshCallback: handleWebSocketChange,
    enabled: subscriptionEnabled
  });

  // Mock reconnect and disconnect functions since the new API doesn't provide them
  const reconnect = useCallback(() => {
    logger.debug('Reconnect requested for subtask WebSocket');
    // The new hook handles reconnection internally
    setReconnectAttempts(0);
  }, []);

  const disconnect = useCallback(() => {
    logger.debug('Disconnect requested for subtask WebSocket');
    // The new hook will handle cleanup when enabled becomes false
  }, []);

  // Auto-reconnect on failure with delay
  useEffect(() => {
    if (!isConnected && subscriptionEnabled && reconnectAttempts > 0 && reconnectAttempts < 5) {
      const delay = 2000 + (reconnectAttempts * 2000); // 2s, 4s, 6s, 8s, 10s

      const timeoutId = setTimeout(() => {
        logger.debug(`Auto-reconnecting WebSocket (attempt ${reconnectAttempts + 1})`);
        reconnect();
      }, delay);

      return () => clearTimeout(timeoutId);
    }
  }, [isConnected, subscriptionEnabled, reconnectAttempts, reconnect]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (createdRefreshTimer.current) {
        clearTimeout(createdRefreshTimer.current);
        createdRefreshTimer.current = null;
      }
    };
  }, []);

  return {
    isConnected,
    reconnect,
    disconnect
  };
}