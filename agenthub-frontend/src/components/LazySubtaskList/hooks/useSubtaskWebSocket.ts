// useSubtaskWebSocket hook - Real-time updates for LazySubtaskList
// Extracted from original LazySubtaskList.tsx during SOLID refactoring

import { useEffect, useCallback, useState } from "react";
import { useChangeSubscription } from "../../../hooks/useChangeSubscription";
import type { UseSubtaskWebSocketReturn, SubtaskChangePayload } from "../types/subtaskTypes";
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
  onSubtaskChanges: () => Promise<void>
): UseSubtaskWebSocketReturn {

  const [isConnected, setIsConnected] = useState(false);
  const [reconnectAttempts, setReconnectAttempts] = useState(0);

  // Debounced change handler to prevent rapid updates
  const debouncedHandleChanges = useCallback(
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

      logger.debug('Subtask WebSocket change received:', {
        type: data.type,
        subtaskId: data.subtask?.id,
        parentTaskId: data.subtask?.parent_task_id || data.parent_task_id
      });

      // Check if this change is relevant to our parent task
      const changeParentTaskId = data.subtask?.parent_task_id || data.parent_task_id;
      if (changeParentTaskId && changeParentTaskId !== parentTaskId) {
        logger.debug('Change not relevant to this parent task, ignoring');
        return;
      }

      // Process the change with debouncing
      await debouncedHandleChanges();

      setReconnectAttempts(0); // Reset on successful message

    } catch (error) {
      logger.error('Error processing WebSocket change:', error);
    }
  }, [parentTaskId, debouncedHandleChanges]);

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
   * Subscribe to WebSocket changes
   */
  const {
    isConnected: changeSubscriptionConnected,
    reconnect,
    disconnect
  } = useChangeSubscription(
    subscriptionEnabled ? [parentTaskId] : [], // Only subscribe when enabled
    handleWebSocketChange,
    {
      onConnectionChange: handleConnectionChange,
      reconnectDelay: 1000 + (reconnectAttempts * 2000), // Exponential backoff
      maxReconnectAttempts: 5
    }
  );

  // Update connection state from subscription hook
  useEffect(() => {
    setIsConnected(changeSubscriptionConnected);
  }, [changeSubscriptionConnected]);

  /**
   * Manual reconnection with retry logic
   */
  const handleReconnect = useCallback(() => {
    if (reconnectAttempts < 5) {
      logger.debug('Attempting to reconnect WebSocket...');
      reconnect();
    } else {
      logger.warn('Max reconnection attempts reached');
    }
  }, [reconnect, reconnectAttempts]);

  /**
   * Clean disconnect
   */
  const handleDisconnect = useCallback(() => {
    logger.debug('Manually disconnecting WebSocket');
    disconnect();
    setReconnectAttempts(0);
  }, [disconnect]);

  // Auto-reconnect on failure with delay
  useEffect(() => {
    if (!isConnected && subscriptionEnabled && reconnectAttempts > 0 && reconnectAttempts < 5) {
      const delay = 2000 + (reconnectAttempts * 2000); // 2s, 4s, 6s, 8s, 10s

      const timeoutId = setTimeout(() => {
        logger.debug(`Auto-reconnecting WebSocket (attempt ${reconnectAttempts + 1})`);
        handleReconnect();
      }, delay);

      return () => clearTimeout(timeoutId);
    }
  }, [isConnected, subscriptionEnabled, reconnectAttempts, handleReconnect]);

  return {
    isConnected,
    reconnectAttempts,
    reconnect: handleReconnect,
    disconnect: handleDisconnect
  };
}